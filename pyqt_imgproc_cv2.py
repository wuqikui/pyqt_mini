"""
PyQt6 综合项目：图片批量处理工具（cv2版本）
包含：多线程、信号槽、文件对话框、图片处理、进度条、日志
"""
import os
import sys
import cv2
import numpy as np
from datetime import datetime
# from PIL import Image, ImageFilter, ImageEnhance  # PIL已替换为cv2
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QProgressBar,
    QComboBox, QSpinBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal, QSize


class Worker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)

    def __init__(self, files, output_dir, operation, quality, parent=None):
        super().__init__(parent)
        self.files = files
        self.output_dir = output_dir
        self.operation = operation
        self.quality = quality
        self._running = True

    def run(self):
        success, failed = 0, 0
        total = len(self.files)
        for i, f in enumerate(self.files):
            if not self._running:
                break
            try:
                self.process_image(f)
                success += 1
                self.log.emit(f"[成功] {os.path.basename(f)}")
            except Exception as e:
                failed += 1
                self.log.emit(f"[失败] {os.path.basename(f)}: {e}")
            self.progress.emit(int((i + 1) / total * 100))
        self.finished.emit(success, failed)

    def stop(self):
        self._running = False

    def process_image(self, filepath):
        # PIL: img = Image.open(filepath)
        # cv2替换：OpenCV默认读取为BGR格式
        img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError("无法读取图片")
        
        name = os.path.splitext(os.path.basename(filepath))[0]
        is_gray = len(img.shape) == 2  # 判断是否为灰度图

        if self.operation == "模糊":
            # PIL: img = img.filter(ImageFilter.GaussianBlur(radius=5))
            # cv2替换：高斯模糊，ksize必须为奇数
            img = cv2.GaussianBlur(img, (11, 11), 5)
        elif self.operation == "锐化":
            # PIL: img = img.filter(ImageFilter.SHARPEN)
            # cv2替换：自定义锐化卷积核
            kernel = np.array([[-1, -1, -1],
                              [-1,  9, -1],
                              [-1, -1, -1]])
            img = cv2.filter2D(img, -1, kernel)
        elif self.operation == "增强对比":
            # PIL: img = ImageEnhance.Contrast(img).enhance(1.5)
            # cv2替换：使用alpha=1.5增强对比度，beta=0
            img = cv2.convertScaleAbs(img, alpha=1.5, beta=0)
        elif self.operation == "转灰度":
            # PIL: img = img.convert("L")
            # cv2替换：BGR转灰度（如果不是灰度图的话）
            if not is_gray:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            is_gray = True  # 更新状态为灰度图
        elif self.operation == "缩放":
            # PIL: img = img.resize((img.width // 2, img.height // 2))
            # cv2替换：缩放为原图的一半
            height, width = img.shape[:2]
            img = cv2.resize(img, (width // 2, height // 2), interpolation=cv2.INTER_AREA)

        # PIL: ext = ".jpg" if img.mode == "RGB" else ".png"
        # cv2替换：根据是否为灰度图选择扩展名
        ext = ".png" if is_gray else ".jpg"
        out_path = os.path.join(self.output_dir, f"{name}_{self.operation}{ext}")
        
        # PIL: img.save(out_path, quality=self.quality)
        # cv2替换：保存图片，注意cv2.imwrite的参数
        if ext == ".jpg":
            # JPEG格式使用quality参数（0-100，越高越好）
            cv2.imwrite(out_path, img, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        else:
            # PNG格式不需要quality参数
            cv2.imwrite(out_path, img)


class ImageProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.files = []
        self.worker = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("图片批量处理器 v1.0 (cv2版)")
        self.setMinimumSize(700, 500)

        menubar = self.menuBar()
        help_menu = menubar.addMenu("帮助")
        help_menu.addAction("关于", self.show_about)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        file_group = QGroupBox("文件选择")
        file_layout = QHBoxLayout()
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet("color: #666; padding: 5px;")
        btn_select = QPushButton("选择图片")
        btn_select.clicked.connect(self.select_files)
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self.clear_files)
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(btn_select)
        file_layout.addWidget(btn_clear)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        opt_group = QGroupBox("处理选项")
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("操作:"))
        self.op_combo = QComboBox()
        self.op_combo.addItems(["模糊", "锐化", "增强对比", "转灰度", "缩放"])
        opt_layout.addWidget(self.op_combo)
        opt_layout.addWidget(QLabel("质量:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(10, 100)
        self.quality_spin.setValue(85)
        opt_layout.addWidget(self.quality_spin)
        opt_layout.addStretch()
        opt_group.setLayout(opt_layout)
        layout.addWidget(opt_group)

        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        layout.addWidget(self.progress)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(150)
        layout.addWidget(self.log_edit)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始处理")
        self.btn_start.setFixedHeight(40)
        self.btn_start.clicked.connect(self.start_process)
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setFixedHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_process)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        self.log("=" * 40)
        self.log(f"[{datetime.now().strftime('%H:%M:%S')}] 程序就绪，请选择图片")

    def log(self, msg):
        self.log_edit.append(msg)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if files:
            self.files = files
            self.file_label.setText(f"已选 {len(files)} 个文件")

    def clear_files(self):
        self.files = []
        self.file_label.setText("未选择文件")

    def start_process(self):
        if not self.files:
            QMessageBox.warning(self, "提示", "请先选择图片")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if not output_dir:
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress.setValue(0)
        self.log_edit.clear()
        self.log(f"[{datetime.now().strftime('%H:%M:%S')}] 开始处理 {len(self.files)} 个文件...")

        self.worker = Worker(
            self.files,
            output_dir,
            self.op_combo.currentText(),
            self.quality_spin.value()
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def stop_process(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.log("[!] 用户停止")

    def on_finished(self, success, failed):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.log(f"[完成] 成功: {success}, 失败: {failed}")

    def show_about(self):
        QMessageBox.about(self, "关于",
            "图片批量处理器 v1.0 (cv2版)\n\n"
            "功能：批量图片处理（模糊、锐化、灰度等）\n"
            "技术：PyQt6 + 多线程QThread + OpenCV\n\n"
            "适合初学者学习的综合性PyQt6项目")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ImageProcessor()
    window.show()
    sys.exit(app.exec())
