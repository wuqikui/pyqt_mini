#include <QApplication>       // Qt应用程序核心类，管理应用生命周期
#include <QMainWindow>        // 主窗口类
#include <QWidget>            // 基础控件容器类
#include <QVBoxLayout>        // 垂直布局管理器
#include <QHBoxLayout>        // 水平布局管理器
#include <QLineEdit>          // 单行文本输入框
#include <QPushButton>        // 按钮控件
#include <QComboBox>          // 下拉选择框
#include <QTextEdit>          // 多行文本编辑框（显示结果）
#include <QScrollBar>         // 滚动条
#include <QProgressBar>       // 进度条
#include <QFileDialog>        // 文件选择对话框
#include <QMessageBox>        // 消息提示框
#include <QDateTime>          // 日期时间类（生成日志文件名）
#include <QFile>              // 文件操作类
#include <QTextStream>        // 文本流（写入日志/文件）
#include <QString>            // Qt字符串类（处理中文更友好）
#include <QStringList>        // Qt字符串列表
#include <QDebug>             // 调试输出
#include <QXlsx/Document>     // QtXlsx核心类（读取Excel）
#include <stdexcept>          // 标准异常类
#include <filesystem>         // C++17文件系统（检查文件存在性）

// 命名空间简化代码（Qt常用）
namespace fs = std::filesystem;

/**
 * @brief Excel数据校验主窗口类
 * 继承QMainWindow：Qt主窗口框架，自带菜单栏/工具栏等（此处简化使用）
 * 功能对应原Python的ExcelDataCheckerApp类
 */
class ExcelDataCheckerWindow : public QMainWindow
{
    // 必须添加此宏：启用Qt元对象系统（信号槽、反射等核心功能）
    Q_OBJECT

public:
    /**
     * @brief 构造函数
     * @param parent 父窗口指针（Qt父子对象机制：父对象销毁时自动销毁子对象，避免内存泄漏）
     */
    ExcelDataCheckerWindow(QWidget* parent = nullptr)
        : QMainWindow(parent)
    {
        // 初始化窗口基本属性
        this->setWindowTitle("Excel数据检查工具");  // 窗口标题
        this->resize(600, 400);                   // 窗口初始尺寸

        // 创建中心控件（QMainWindow必须设置centralWidget）
        QWidget* centralWidget = new QWidget(this);
        this->setCentralWidget(centralWidget);

        // 创建主布局（垂直布局）
        QVBoxLayout* mainLayout = new QVBoxLayout(centralWidget);
        mainLayout->setSpacing(10);  // 控件间距
        mainLayout->setContentsMargins(10, 10, 10, 10);  // 布局边距

        // ========== 1. 文件选择区域 ==========
        QHBoxLayout* fileLayout = new QHBoxLayout();  // 水平布局
        // 文本输入框：显示选中的Excel路径
        m_excelPathEdit = new QLineEdit(this);
        m_excelPathEdit->setPlaceholderText("请选择Excel文件");  // 占位提示
        m_excelPathEdit->setReadOnly(true);  // 只读（仅通过按钮选择）
        fileLayout->addWidget(m_excelPathEdit);

        // 选择文件按钮
        QPushButton* selectFileBtn = new QPushButton("选择", this);
        // 信号槽绑定：按钮点击 → 触发selectExcelFile函数
        // connect是Qt核心机制：解耦控件事件和业务逻辑
        connect(selectFileBtn, &QPushButton::clicked, this, &ExcelDataCheckerWindow::selectExcelFile);
        fileLayout->addWidget(selectFileBtn);

        mainLayout->addLayout(fileLayout);  // 将文件布局加入主布局

        // ========== 2. 区域选择区域 ==========
        QHBoxLayout* areaLayout = new QHBoxLayout();
        // 区域标签
        QLabel* areaLabel = new QLabel("区域：", this);
        areaLayout->addWidget(areaLabel);

        // 区域下拉框
        m_areaComboBox = new QComboBox(this);
        // 设置下拉选项（对应原Python的area_options）
        QStringList areaOptions = { "全部", "A区", "B区", "C区" };
        m_areaComboBox->addItems(areaOptions);
        m_areaComboBox->setCurrentIndex(0);  // 默认选中"全部"
        areaLayout->addWidget(m_areaComboBox);

        mainLayout->addLayout(areaLayout);

        // ========== 3. 结果显示区域 ==========
        QLabel* resultLabel = new QLabel("异常数据：", this);
        mainLayout->addWidget(resultLabel);

        // 结果文本框（多行）
        m_resultTextEdit = new QTextEdit(this);
        m_resultTextEdit->setReadOnly(true);  // 只读（仅显示结果）
        m_resultTextEdit->setLineWrapMode(QTextEdit::WidgetWidth);  // 自动换行
        mainLayout->addWidget(m_resultTextEdit);

        // ========== 4. 进度条 ==========
        m_progressBar = new QProgressBar(this);
        m_progressBar->setRange(0, 100);  // 进度范围0-100
        m_progressBar->setValue(0);       // 初始值0
        mainLayout->addWidget(m_progressBar);

        // ========== 5. 检查按钮 ==========
        QPushButton* checkBtn = new QPushButton("检查", this);
        connect(checkBtn, &QPushButton::clicked, this, &ExcelDataCheckerWindow::checkExcelData);
        // 按钮右对齐（通过水平布局实现）
        QHBoxLayout* btnLayout = new QHBoxLayout();
        btnLayout->addStretch();  // 左侧拉伸（按钮右对齐）
        btnLayout->addWidget(checkBtn);
        mainLayout->addLayout(btnLayout);

        // 初始化日志目录
        initLogDirectory();
    }

private slots:
    /**
     * @brief 选择Excel文件槽函数（响应按钮点击）
     * 对应原Python的select_file方法
     */
    void selectExcelFile()
    {
        // 打开文件选择对话框
        // 参数：父窗口、标题、默认路径、文件类型过滤器
        QString filePath = QFileDialog::getOpenFileName(
            this,
            "选择Excel文件",
            QDir::currentPath(),  // 默认路径：当前工作目录
            "Excel文件 (*.xls *.xlsx);;所有文件 (*.*)"
        );

        // 如果用户选择了文件（非空），更新输入框内容
        if (!filePath.isEmpty())
        {
            m_excelPathEdit->setText(filePath);
        }
    }

    /**
     * @brief 校验Excel数据槽函数（响应检查按钮）
     * 对应原Python的check_data方法
     */
    void checkExcelData()
    {
        // 重置界面状态
        m_resultTextEdit->clear();  // 清空结果框
        m_progressBar->setValue(0); // 进度条归零

        // 1. 验证文件路径
        QString excelPath = m_excelPathEdit->text();
        if (excelPath.isEmpty() || excelPath == "请选择Excel文件")
        {
            QMessageBox::critical(this, "错误", "请选择有效的Excel文件！");
            return;
        }
        // 检查文件是否存在（C++17 filesystem）
        if (!fs::exists(excelPath.toStdString()))
        {
            QMessageBox::critical(this, "错误", "所选文件不存在！");
            return;
        }

        try
        {
            // 2. 读取Excel文件（QtXlsx核心操作）
            m_progressBar->setValue(20);  // 更新进度条
            QApplication::processEvents();  // 强制刷新界面（避免卡顿）

            // 创建QXlsx文档对象（打开Excel文件）
            QXlsx::Document xlsxDoc(excelPath);
            if (!xlsxDoc.load())  // 检查文件是否加载成功
            {
                throw std::runtime_error("Excel文件加载失败（可能格式不支持）");
            }

            // 获取Excel的行数和列数（QtXlsx从1开始计数，和Excel一致）
            int rowCount = xlsxDoc.dimension().rowCount();
            int colCount = xlsxDoc.dimension().columnCount();
            if (rowCount <= 1)  // 只有标题行（无数据）
            {
                QMessageBox::information(this, "提示", "Excel文件中无有效数据！");
                return;
            }

            // 3. 获取选中的区域
            m_progressBar->setValue(40);
            QApplication::processEvents();
            QString selectedArea = m_areaComboBox->currentText();

            // 4. 逐行校验数据
            m_progressBar->setValue(60);
            QApplication::processEvents();
            QStringList errorList;  // 存储异常信息（Qt字符串列表，替代Python的list）

            // 遍历数据行（从第2行开始，第1行是标题）
            for (int row = 2; row <= rowCount; ++row)
            {
                // 存储当前行的异常信息
                QStringList rowErrors;

                // ===== 读取单元格值 =====
                // 假设："区域"列是第1列（A列），"地号"列是第2列（B列），"土地性质"列是第3列（C列）
                // QtXlsx::Cell::value()返回QVariant（Qt通用数据类型，可转换为QString/int等）
                QString area = xlsxDoc.cellAt(row, 1)->value().toString().trimmed();
                QString landNo = xlsxDoc.cellAt(row, 2)->value().toString().trimmed();
                QString landType = xlsxDoc.cellAt(row, 3)->value().toString().trimmed();

                // ===== 筛选区域 =====
                if (selectedArea != "全部" && area != selectedArea)
                {
                    continue;  // 跳过非目标区域的数据
                }

                // ===== 校验地号 =====
                if (landNo.isEmpty() || landNo == "NaN")  // 对应Python的pd.isna
                {
                    rowErrors.append("地号为空");
                }

                // ===== 校验土地性质 =====
                if (landType.isEmpty() || !(landType == "国有" || landType == "集体"))
                {
                    rowErrors.append("土地性质值不合法");
                }

                // ===== 记录异常 =====
                if (!rowErrors.isEmpty())
                {
                    QString errorMsg = QString("第%1行数据，%2；")
                        .arg(row)  // 替换占位符%1为行号
                        .arg(rowErrors.join(", "));  // 拼接异常信息
                    errorList.append(errorMsg);
                }
            }

            // 5. 显示校验结果
            m_progressBar->setValue(80);
            QApplication::processEvents();
            if (errorList.isEmpty())
            {
                m_resultTextEdit->setText("没有发现不符合标准的数据");
            }
            else
            {
                m_resultTextEdit->setText(errorList.join("\n"));  // 换行显示所有异常
            }

            // 6. 完成校验
            m_progressBar->setValue(100);
            QMessageBox::information(this, "提示", "检查完毕！");
        }
        catch (const std::exception& e)
        {
            // 捕获异常并记录日志
            QString errorMsg = QString("程序异常：%1").arg(e.what());
            QMessageBox::critical(this, "错误", errorMsg);
            writeLog(errorMsg);  // 写入日志文件
            m_progressBar->setValue(0);
        }
    }

private:
    /**
     * @brief 初始化日志目录
     */
    void initLogDirectory()
    {
        // Qt的QDir类：目录操作
        QDir logDir("logs");
        if (!logDir.exists())  // 如果目录不存在
        {
            logDir.mkdir(".");  // 创建当前目录（即logs）
        }
    }

    /**
     * @brief 写入日志文件
     * @param logMsg 日志内容
     */
    void writeLog(const QString& logMsg)
    {
        // 生成时间戳（格式：年月日_时分秒）
        QString timestamp = QDateTime::currentDateTime().toString("yyyyMMdd_hhmmss");
        QString logFilePath = QString("logs/error_%1.log").arg(timestamp);

        // 打开日志文件（追加模式，UTF-8编码）
        QFile logFile(logFilePath);
        if (logFile.open(QIODevice::WriteOnly | QIODevice::Text))
        {
            QTextStream logStream(&logFile);
            logStream.setCodec("UTF-8");  // 设置编码（避免中文乱码）
            // 写入日志（时间+内容）
            logStream << QDateTime::currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
                << " - ERROR - " << logMsg << endl;
            logFile.close();
        }
    }

    // 控件成员变量（类内访问）
    QLineEdit* m_excelPathEdit = nullptr;    // Excel路径输入框
    QComboBox* m_areaComboBox = nullptr;     // 区域下拉框
    QTextEdit* m_resultTextEdit = nullptr;   // 结果显示框
    QProgressBar* m_progressBar = nullptr;   // 进度条
};

/**
 * @brief 程序入口函数
 * Qt应用程序的标准入口：QApplication → 创建窗口 → 显示 → 运行事件循环
 */
int main(int argc, char* argv[])
{
    // 创建Qt应用程序对象（argc/argv传递命令行参数）
    QApplication app(argc, argv);

    // 创建主窗口对象
    ExcelDataCheckerWindow window;
    window.show();  // 显示窗口（Qt控件默认隐藏，需手动show）

    // 运行应用程序事件循环（阻塞，直到窗口关闭）
    return app.exec();
}

// 必须添加此行：Qt元对象系统的实现（Q_OBJECT宏依赖）
#include "main.moc"