import os
import sys
import pandas as pd
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QProgressBar,
    QComboBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt


class DataCheckerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.excel_path = ""
        self.init_ui()
        self.setup_logging()

    def setup_logging(self):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"error_{timestamp}.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def init_ui(self):
        self.setWindowTitle("检查工具")
        self.setMinimumSize(600, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        file_group = QGroupBox("文件选择")
        file_layout = QHBoxLayout()
        self.file_label = QLabel("请选择Excel文件:")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        btn_select = QPushButton("选择")
        btn_select.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(btn_select)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        area_group = QGroupBox("区域选择")
        area_layout = QHBoxLayout()
        area_layout.addWidget(QLabel("区域:"))
        self.area_combo = QComboBox()
        self.area_combo.addItems(["全部", "A区", "B区", "C区"])
        self.area_combo.setCurrentText("全部")
        area_layout.addWidget(self.area_combo)
        area_layout.addStretch()
        area_group.setLayout(area_layout)
        layout.addWidget(area_group)

        result_group = QGroupBox("异常数据")
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_check = QPushButton("检查")
        self.btn_check.setFixedSize(100, 30)
        self.btn_check.clicked.connect(self.check_data)
        btn_layout.addWidget(self.btn_check)
        layout.addLayout(btn_layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "请选择Excel文件", "",
            "Excel文件 (*.xls *.xlsx);;所有文件 (*.*)"
        )
        if file_path:
            self.excel_path = file_path
            self.file_label.setText(file_path)

    def check_data(self):
        self.result_text.clear()
        self.progress.setValue(0)

        if not self.excel_path:
            QMessageBox.critical(self, "错误", "程序发生异常！")
            return

        if not os.path.exists(self.excel_path):
            QMessageBox.critical(self, "错误", "程序发生异常！")
            return

        try:
            self.progress.setValue(20)
            QApplication.processEvents()

            df = pd.read_excel(self.excel_path)
            if df.empty:
                QMessageBox.information(self, "提示", "Excel文件中没有数据！")
                return

            self.progress.setValue(40)
            QApplication.processEvents()

            selected_area = self.area_combo.currentText()
            if selected_area != "全部":
                area_code = selected_area
                df = df[df['区域'] == area_code]

            errors = []
            for index, row in df.iterrows():
                error_msgs = []

                if pd.isna(row['地号']) or str(row['地号']).strip() == "":
                    error_msgs.append("地号为空")

                land_type = str(row['土地性质']).strip()
                if pd.isna(row['土地性质']) or land_type == "" or (land_type not in ["国有", "集体"]):
                    error_msgs.append("土地性质值不合法")

                if error_msgs:
                    errors.append(f"第{index + 2}行数据，{', '.join(error_msgs)}；")

            self.progress.setValue(80)
            QApplication.processEvents()

            if errors:
                self.result_text.setPlainText("\n".join(errors))
            else:
                self.result_text.setPlainText("没有发现不符合标准的数据")

            self.progress.setValue(100)
            QMessageBox.information(self, "提示", "检查完毕！")

        except Exception:
            logging.error("数据检查异常", exc_info=True)
            QMessageBox.critical(self, "错误", "程序发生异常！")
            self.progress.setValue(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = DataCheckerApp()
    window.show()
    sys.exit(app.exec())