# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

from PyQt5.QtWidgets import QMainWindow, QMessageBox, QApplication, QFileDialog
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from sys import argv, exit
from numpy import array as nparray
from PIL.Image import open as imopen
from PIL.Image import fromarray as imfromarray
from win32gui import GetWindowText, GetForegroundWindow
from qimage2ndarray import array2qimage
from shutil import move
from os import makedirs, chdir, getcwd
from os import path as ospath
from utils import read_labelme_json, return_bboxImg, dump_json, list_all_type_of_image, resize_widget, resize_font, resize_icon
from MainWindow import resource_path, Ui_MainWindow, progressWindow
from glob import glob
import pandas as pd
import numpy as np

keymap = {}
img_type = ""
for key, value in vars(Qt).items():
    if isinstance(value, Qt.Key):
        temp = key.partition('_')[2]
        if len(temp)==1 or temp=='Backspace':
            keymap[value] = temp 
            
desired_window = "Quick Classification"



class mainProgram(QMainWindow, Ui_MainWindow):
    keyPressed = pyqtSignal(QEvent)
    def __init__(self, parent=None, label_dict={}):
        super(mainProgram, self).__init__(parent)
        self.label_dict = label_dict
        print(label_dict)

        self.setupUi(self, label_dict)
        # self.clipButton.clicked.connect(self.clip_by_path)
        # self.MergeButton.clicked.connect(self.merge_2_json)
        self.pathButton.clicked.connect(self.select_path)
        self.prevButton.clicked.connect(self.prev_image)
        self.saveButton.clicked.connect(self.save)
        self.keyPressed.connect(self.on_key)
        self.setStyleSheet("QMessageBox { messagebox-text-interaction-flags: 5; }")
        self.path_click=False

    # If user resize mainwindow, then keep the button position    
    def resizeEvent(self, event):
        for i in [self.img_qlabel, self.text_qlabel, self.scroll,   self.separate_line, self.pathButton, self.prevButton, self.saveButton, self.clipButton]:
            resize_widget(i, self.rect().width(), self.rect().height())
        for i in [self.img_qlabel, self.text_qlabel,  self.pathButton, self.prevButton, self.saveButton]:
            resize_font(i, self.rect().width(), self.rect().height())
        for i in [ self.pathButton, self.prevButton, self.saveButton]:
            resize_icon(i, self.rect().width(), self.rect().height())
        
        try:
            bbox = self.read_img(self.image_list[self.imgnumber])
            self.update_image(bbox)
        except:
            pass
            
        QMainWindow.resizeEvent(self, event)
        
    # this function is for reading image using pillow package
    def read_img(self, path):
        if not ospath.exists(path):
            QMessageBox.information(self, "Warning", f"No image found : {path}")
            exit(app.exec_())
        else:
            return nparray(imopen(path))
    # this function is for merging clipped bounding box which is already classified by folder back to labelme json format        
    def merge_2_json(self):
        print("合併至Json")
        path = QFileDialog.getExistingDirectory(caption = '選擇ClippedBBox資料夾')
        json_list = glob(ospath.join(ospath.dirname(path),"*.json"))
        json_img_list = []
        for i in json_list:
            img_path = ospath.join(ospath.dirname(i),ospath.basename(i).replace(".json","")+".*")
            json_img_list.extend(glob(img_path))
        if len(json_list)!=0 and int(len(json_list)*2)==len(json_img_list):
            ClippedBBox_loc = "children"
        else:
            ClippedBBox_loc = "parent"
        if ospath.basename(path)!="ClippedBBox":
            QMessageBox.information(self, "Warning", f"不正確的路徑，請選擇ClippedBBox資料夾")
        else:
            reply = QMessageBox.question(self, 'Warning', 
                             f'確定要將分類完成的Bounding Box類別覆蓋{ospath.dirname(path)}下的所有Json檔嗎?', QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                box_list = glob(path+"/**/*."+img_type,recursive=True)
                json_out = []
                progress_window = progressWindow(len(box_list),'正在合併回Json...')
                for j,i in enumerate(box_list):
                    progress_window.set_progress_value(j+1)
                    QApplication.processEvents()
                    class_ = ospath.basename(ospath.dirname(i))
                    split_name = ospath.basename(i).split("-")
                    dataset_name = split_name[0]
                    image_name = split_name[1]
                    box_id = split_name[2].split(".")[0]
                    if ClippedBBox_loc == 'parent':
                        json_path = ospath.join(ospath.dirname(path),dataset_name,image_name+".json")
                    elif ClippedBBox_loc=="children":
                        json_path = ospath.join(ospath.dirname(path),image_name+".json")
                    json_out_temp = dump_json(json_path,box_id,class_)
                    json_out.append(json_out_temp)
                QMessageBox.information(self, "Warning", f"合併完成，Json讀取共{json_out.count(True)}個成功，{json_out.count(False)}個失敗")
            else:
                QMessageBox.information(self, "Warning", f"使用者已取消")
     
    # this function is for clipping bounding box and save into ClippedBBox folder with specific file name which can merge back to labelme json format after classified by folder    
    def clip_by_path(self):
        print("裁剪BoundingBox")
        path = QFileDialog.getExistingDirectory()
        json_list = glob(path+"/*/*.json",recursive=True)
        if len(json_list)==0:
            json_list = glob(path+"/*.json",recursive=True)    
        if len(path) == 0:
            QMessageBox.information(self,"Warning", "Please select a valid path!")
        elif len(json_list)==0:
            QMessageBox.information(self,"Warning", "沒有找到任何Json檔")
        else:
            if not ospath.exists(path+'/ClippedBBox'):
                makedirs(path+'/ClippedBBox')        
            missing_count = 0
            success_count = 0
            progress_window = progressWindow(len(json_list),'正在裁剪Bounding Box...')
            for j,i in enumerate(json_list):
                progress_window.set_progress_value(j+1)
                QApplication.processEvents()
                try:
                    dataset_name = ospath.basename(ospath.dirname(i))
                    json_content = read_labelme_json(i)
                    img_path = ospath.join(ospath.dirname(i),json_content[0])
                    img = self.read_img(img_path)
                    for count,b in enumerate(json_content[1]):
                        if not ospath.exists(path+'/ClippedBBox/'+b[0]):
                            makedirs(path+'/ClippedBBox/'+b[0])
                        cropped_box = imfromarray(return_bboxImg(img,b))
                        cropped_box.save(path+"/ClippedBBox/"+b[0]+"/"+dataset_name+"-"+json_content[0].split(".")[0]+"-"+str(count)+"."+img_type,"JPEG")
                    success_count+=1
                except:
                    missing_count += 1
            QMessageBox.information(self, "Warning", f"裁剪完成，Json讀取共{success_count}個成功，{missing_count}個失敗\nBounding Box儲存於{path+'/ClippedBBox/'}")
            
    # this function is for saveing current classification progress
    def save(self):
        print("存檔中...")
        if not self.path_click:
            QMessageBox.information(self, "Warning", "Please select folder first!")
        elif len(self.new_class)==0:
            QMessageBox.information(self, "Warning", "No images need to be saved!")
        else:
            progress_window = progressWindow(len(self.done_img_list),'正在儲存...')

            # 输出到文件
            output_file = open(ospath.dirname(getcwd())+"/"+"label.csv", 'a')
            for i in range(len(self.done_img_list)):
                output_file.write(self.done_img_list[i]+","+self.new_class[i]+","+label_dict[self.new_class[i]])
                output_file.write("\n")

            for j, (im, c) in enumerate(zip(self.done_img_list, self.new_class)):
                progress_window.set_progress_value(j+1)
                QApplication.processEvents()
            output_file.close()
                # output_path = ospath.dirname(getcwd())+"/"+ospath.basename(getcwd())+"/"+"已完成"
                # print(output_path)
                # if not ospath.exists(output_path):
                #     makedirs(output_path)
                # move(im, ospath.join(output_path,ospath.basename(im)))
            
            self.image_list = list_all_type_of_image()
            self.imgnumber = 0
            self.new_class = []
            self.done_img_list = []
            df = pd.read_csv(ospath.dirname(getcwd())+"/"+"label.csv", encoding="gbk")
            try:
                df = pd.read_csv(ospath.dirname(getcwd()) + "/" + "label.csv")
                # print(df)
                # print(np.array(df["name"]))
                for i in self.image_list:
                    if i in np.array((df["name"])):
                        # self.image_list.remove(i)
                        self.imgnumber+=1
                        # print("ok")
            except:
                pass

            if self.to_the_end:
                QMessageBox.information(self, "Warning", "Job Done!")
                exit(app.exec_())
            else:
                bbox = self.read_img(self.image_list[self.imgnumber])
                self.update_image(bbox)            
                QMessageBox.information(self, "Warning", "Image saved!")


    # this function is for select image folder which is wait to be classified
    def select_path(self):
        print("選擇圖片路徑")
        path = QFileDialog.getExistingDirectory()
        self.to_the_end = False
        if len(path) == 0:
            QMessageBox.information(self,"Warning", "Please select a valid path!")
        else:
            chdir(path)
            self.image_list = list_all_type_of_image()


            try:
                df = pd.read_csv(ospath.dirname(getcwd()) + "/" + "label.csv", encoding="gbk")
                self.image_list = self.image_list[len(np.array((df["name"]))):]

            except:
                output_file = open(ospath.dirname(getcwd()) + "/" + "label.csv", 'w+')
                output_file.write("name, label, label_name")
                output_file.write("\n")
                pass

            if len(self.image_list)==0:
                QMessageBox.information(self,"Warning", "No images found!")
            else:
                self.imgnumber = 0
                self.new_class = []
                self.done_img_list = []
                self.path_click = True
                bbox = self.read_img(self.image_list[self.imgnumber])
                self.update_image(bbox)
    
    # this function is for update current window to the next image after user click classification button
    def update_image(self, bbox):
        qImg = array2qimage(bbox)
        pixmap = QPixmap(qImg)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(self.img_qlabel.width(), self.img_qlabel.height(), Qt.KeepAspectRatio)
            self.img_qlabel.setPixmap(pixmap)
            try : 
                split_imgName = self.image_list[self.imgnumber].split("-")
                text = ""
                text += f" Dataset name : {ospath.basename(split_imgName[0])}"
                text += f"\n Image name : {split_imgName[1]}."+img_type
                text += f"\n BBox id : {split_imgName[2].replace('.'+img_type,'')}"
            except:
                text = " Filename : "+ospath.basename(self.image_list[self.imgnumber])
            text += "\n\n"+f" Current progress : {self.imgnumber+1}/{len(self.image_list)}"
            # text += f"\n {self.imgnumber} images haven't been saved"
            self.text_qlabel.setText(text)
    
    # when user press any keys will trigger this function        
    def keyPressEvent(self, event):
        super(mainProgram, self).keyPressEvent(event)
        self.keyPressed.emit(event) 
    # when user press any keys will trigger this function           
    def on_key(self, event):
        current_window = GetWindowText(GetForegroundWindow())
        if current_window==desired_window:
            if event.key() in keymap:
                if keymap[event.key()]=='Backspace':
                    self.prev_image()
                elif keymap[event.key()]=='A'or keymap[event.key()]=='D':
                    self.new_class.append(keymap[event.key()])
                    self.done_img_list.append(self.image_list[self.imgnumber])
                    
                    self.imgnumber += 1
                    
                    # If to the end, save and close program
                    if self.imgnumber==len(self.image_list):
                        self.to_the_end = True
                        self.save()
                    else:
                        bbox = self.read_img(self.image_list[self.imgnumber])
                        self.update_image(bbox)
            else:
                QMessageBox.information(self,"Warning", "Can not press special keys!")
                
    # when user click previous button or 'Backspace' on keyboard will trigger this function to go back to previous image
    def prev_image(self):
        print("返回上一張圖片")
        if self.imgnumber==0:
            QMessageBox.information(self,"Warning", "No previous image!")
        else:
            self.imgnumber -= 1
            self.new_class = self.new_class[:-1]
            self.done_img_list = self.done_img_list[:-1]
            
            bbox = self.read_img(self.image_list[self.imgnumber])
            self.update_image(bbox)

label_dict = {}
if __name__ == '__main__':
    label0 = input("0 is:")
    label1 = input("1 is:")
    img_type = input("input image type:")
    label_dict['A'] = label0
    label_dict['D'] = label1

    app = QApplication(argv)
    app.setWindowIcon(QIcon(resource_path('main.ico')))
    main = mainProgram(label_dict=label_dict)
    main.show()
    exit(app.exec_())
    
 


