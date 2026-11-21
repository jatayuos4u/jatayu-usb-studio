#include <QDialogButtonBox>
#include <QTabWidget>
#include <QSignalBlocker>
#include <QApplication>
#include <QMainWindow>
#include <QCloseEvent>
#include <QPlainTextEdit>
#include <functional>
#include <cstring>
#include <unistd.h>
#include <QWidget>
#include <QFrame>
#include <QLabel>
#include <QPushButton>
#include <QLineEdit>
#include <QInputDialog>
#include <QComboBox>
#include <QListView>
#include <QPalette>
#include <QCheckBox>
#include <QSettings>
#include <QFileDialog>
#include <QDir>
#include <QDialog>
#include <QMessageBox>
#include <QProcess>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QTimer>
#include <QFileInfo>
#include <QHash>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QScrollArea>
#include <QStackedWidget>
#include <QPainter>
#include <QPainterPath>
#include <QStyle>
#include <QIcon>
#include <QFile>
#include <QSaveFile>
#include <QTextStream>
#include <QStorageInfo>
#include <QSet>
#include <QFileSystemModel>
#include <QSizePolicy>
#include <QPointer>
#include <QDesktopServices>
#include <QUrl>
#include <QSysInfo>
#include <QGraphicsDropShadowEffect>
#include <QMouseEvent>
#include <QProgressBar>
#include <QCryptographicHash>
#include <QRegularExpression>
#include <QThread>
#include <QTemporaryDir>
#include <QDateTime>
#include <cmath>
#include <algorithm>
#include <memory>

static constexpr char studioVersion[] = "1.1.0 RC1";
struct Partition { QString path, fs; quint64 bytes; };

struct Drive { QString path, name, size, detail, partitionSummary, identity, sequence; QList<Partition> partitions; QString filesystem; quint64 bytes=0; bool mounted=false, readOnly=false; };
// Beta 30: all UI device views request the same lsblk snapshot schema.
static QStringList usbLsblkArguments() {
    return {"-J", "-b", "-o", "NAME,PATH,SIZE,TRAN,MODEL,TYPE,RM,RO,VENDOR,FSTYPE,MOUNTPOINTS,PTTYPE,SERIAL,WWN"};
}
static quint64 usbBytes(const QJsonObject &obj) {
    bool ok=false;
    const auto value=obj.value("size").toVariant().toString().toULongLong(&ok);
    return ok ? value : 0;
}
static bool usbDisk(const QJsonObject &obj) {
    return obj.value("type").toString()=="disk" && obj.value("tran").toString().toLower()=="usb"
        && obj.value("rm").toVariant().toBool()
        && obj.value("path").toString().startsWith("/dev/") && usbBytes(obj)>0;
}
static QString readDiskSequence(const QString &name) {
    QFile file("/sys/class/block/"+name+"/diskseq");
    if(!file.open(QIODevice::ReadOnly))return {};
    bool valid=false;
    const auto generation=file.readAll().trimmed().toULongLong(&valid);
    return valid && generation?QString::number(generation):QString();
}
static int usbPartitionCount(const QJsonObject &disk) {
    int count=0;
    for (const auto &entry: disk.value("children").toArray())
        if(entry.toObject().value("type").toString()=="part") ++count;
    return count;
}
static QString usbIdentity(const QJsonObject &disk) {
    return disk.value("path").toString()+"|"+disk.value("model").toString().trimmed()
        +"|"+QString::number(usbBytes(disk))+"|"+disk.value("serial").toString()
        +"|"+disk.value("wwn").toString();
}
// Beta 37: advisory GUI fingerprint, never a write-authorization token.
static QString guiFingerprint(const QJsonObject &disk) {
    const QString serial=disk.value("serial").toString().trimmed();
    const QString wwn=disk.value("wwn").toString().trimmed();
    if(serial.isEmpty() && wwn.isEmpty()) return {}; // fail closed
    QStringList parts;
    for(const auto &v:disk.value("children").toArray()) {
        const auto part=v.toObject();
        if(part.value("type").toString()!="part") continue;
        parts<<part.value("path").toString()+":"+part.value("size").toVariant().toString()
            +":"+part.value("fstype").toString();
    }
    parts.sort();
    return usbIdentity(disk)+"|"+parts.join(";");
}
static bool advisoryBaselineMatches(const Drive &drive,const QString &baseline){
    return !drive.sequence.isEmpty() && !baseline.isEmpty() && drive.identity==baseline;
}
static QString sizeText(quint64 bytes) {
    const char* units[]={"B","KiB","MiB","GiB","TiB","PiB"};
    double n=double(bytes); int i=0;
    while(n>=1024.0 && i<5){n/=1024.0;++i;}
    return QString::number(n,'f',i?1:0)+" "+units[i];
}
static QLabel* txt(const QString &s,int pt=11,bool bold=false,const QString &color="#142644") {
    auto *w=new QLabel(s);w->setTextFormat(Qt::PlainText);w->setWordWrap(true);w->setStyleSheet("color:"+color+";background:transparent;");
    QFont f=w->font();f.setPointSize(pt);f.setBold(bold);w->setFont(f);return w;
}
static QFrame* frame(const QString &id) {auto *w=new QFrame;w->setObjectName(id);return w;}
static QVBoxLayout* column(QWidget *w,int gap=8,int margin=14){auto *l=new QVBoxLayout(w);l->setSpacing(gap);l->setContentsMargins(margin,margin,margin,margin);return l;}
class Banner:public QFrame {
public:
    Banner(){setFixedHeight(166);setSizePolicy(QSizePolicy::Expanding,QSizePolicy::Fixed);}
protected:
    void paintEvent(QPaintEvent*) override {
        QPainter p(this);p.setRenderHint(QPainter::Antialiasing);
        QRectF r=rect().adjusted(1,1,-2,-2);
        QPainterPath clip;clip.addRoundedRect(r,18,18);p.setClipPath(clip);
        QLinearGradient bg(0,0,width(),height());
        bg.setColorAt(0,QColor("#09286d"));bg.setColorAt(.48,QColor("#0756c6"));bg.setColorAt(.82,QColor("#0837a2"));bg.setColorAt(1,QColor("#3626a0"));
        p.fillRect(rect(),bg);
        QPainterPath wave;wave.moveTo(width()*.45,height());
        wave.cubicTo(width()*.64,height()*.72,width()*.70,height()*.2,width(),height()*.05);
        p.setPen(QPen(QColor(35,197,255,105),3));p.drawPath(wave);
        QPixmap art(":/assets/hero-overlay.png");
        if(!art.isNull()) {
            QRectF area(width()*.63,8,width()*.36,height()-16);
            QSizeF fitted=art.size();fitted.scale(area.size(),Qt::KeepAspectRatio);
            QRectF dest(area.right()-fitted.width(),area.center().y()-fitted.height()/2,fitted.width(),fitted.height());
            p.drawPixmap(dest,art,QRectF(art.rect()));
        }
        p.setBrush(Qt::NoBrush);p.setPen(QPen(QColor("#4e92ff"),1.6));p.drawRoundedRect(r,18,18);
    }
};
static QIcon studioIcon(const QString &name){return QIcon(":/assets/"+name+".png");}
class Studio:public QMainWindow {
    Q_OBJECT
    QStringList names={"Home","Create Bootable USB","Clone USB","Format USB","Verify USB","USB Repair","Device Safety","Settings","About","Downloads"};
    QList<QPushButton*> nav;
    QStackedWidget *pages=nullptr;
    QLabel *status=nullptr,*deviceInfo=nullptr,*identityStatus=nullptr;
    QString baselinePath, baselineIdentity;
    bool baselineRequested=false;
    bool automaticInitialBaseline=false;
    bool identityAlert=false;
    bool baselineInitialized=false;
    QLabel *safetySummary=nullptr,*safetyDetails=nullptr,*eventHistory=nullptr;
    QComboBox *eventFilterChoice=nullptr;
    struct SafetyEvent { QString timestamp, severity, message; };
    QVector<SafetyEvent> safetyEvents;
    QString lastEventKey;
    void renderSafetyEvents(){
        if(!eventHistory)return;
        const QString filter=eventFilterChoice?eventFilterChoice->currentData().toString():QString("all");
        QStringList rows;
        for(const auto &e:safetyEvents){
            if(filter!="all" && filter!=e.severity)continue;
            rows<<e.timestamp+"  ["+e.severity.toUpper()+"]  "+e.message;
        }
        eventHistory->setText(rows.isEmpty()?"No events in this category yet.":rows.join("\n"));
    }
    void exportSafetyEvents(){
        // Exclusive creation: never overwrite an existing file or follow a final-component symlink.
        if(safetyEvents.isEmpty()){
            QMessageBox::information(this,"Safety history","No safety events to export yet.");return;
        }
        const QString path=QFileDialog::getSaveFileName(this,"Export safety event history",QDir::homePath()+"/jatayu-usb-safety-events.txt","Text files (*.txt)");
        if(path.isEmpty())return;
        const QFileInfo info(path);
        const QString absolute=info.absoluteFilePath();
        if(!QDir::isAbsolutePath(path) || absolute=="/dev" || absolute.startsWith("/dev/") ||
           absolute=="/proc" || absolute.startsWith("/proc/") ||
           absolute=="/sys" || absolute.startsWith("/sys/") ||
           info.isSymLink() || info.exists() || !info.dir().exists()){
            QMessageBox::warning(this,"Export refused","Choose a new file in an existing normal directory. Existing files, symbolic links and system device paths are not allowed.");return;
        }
        QByteArray output="Jatayu USB Studio - read-only device safety history\n";
        output+="Current application session; advisory inspection only; no disk write authorization.\n\n";
        for(const auto &event:safetyEvents){
            output+=(event.timestamp+"  ["+event.severity.toUpper()+"]  "+event.message+"\n").toUtf8();
        }
        // QFile supports NewOnly as an exclusive create (O_EXCL). QSaveFile with NewOnly
        // can fail with an unhelpful error on Qt versions shipped by Debian 13.
        QFile file(absolute);
        if(!file.open(QIODevice::WriteOnly|QIODevice::NewOnly)){
            QMessageBox::warning(this,"Export failed","Could not create the file:\n"+file.errorString()+"\n\nChoose a new filename in a writable folder.");return;
        }
        const qint64 bytes=file.write(output);
        const bool flushed=(bytes==output.size() && file.flush());
        const QString writeError=file.errorString();
        file.close();
        if(!flushed || file.error()!=QFileDevice::NoError){
            QFile::remove(absolute); // Best-effort cleanup of incomplete export.
            QMessageBox::warning(this,"Export failed","Unable to finish writing the safety history:\n"+writeError);return;
        }
        QMessageBox::information(this,"Export complete","Safety history saved to:\n"+absolute);
    }
    QString lastSafetyState, lastDeviceSignature;
    void recordSafetyEvent(const QString &message,const QString &severity="info"){
        // Suppress consecutive duplicate events without suppressing later state transitions.
        const QString key=severity+":"+message;
        if(lastEventKey==key)return;
        lastEventKey=key;
        safetyEvents.prepend({QDateTime::currentDateTime().toString("yyyy-MM-dd hh:mm:ss"),severity,message});
        while(safetyEvents.size()>40)safetyEvents.removeLast();
        renderSafetyEvents();
    }
    QComboBox *target=nullptr;
    QLineEdit *iso=nullptr;
    QLabel *isoStatus=nullptr;
    QVector<Drive> devices;
    QSettings preferences{"JatayuOS","Jatayu USB Studio"};
    QTimer refreshTimer;
    QTimer backendTimer;
    QProcess *backendProbe=nullptr;
    QLabel *backendStatus=nullptr;
    QProcess *scan=nullptr;
    QString selectedPath;
    QProcess *fileDemo=nullptr;
    QProcess *operation=nullptr;
    QList<QComboBox*> operationChoices;
    QTemporaryDir *cancelDirectory=nullptr;
    QByteArray demoBuffer;
public:
    Studio(){
        setWindowTitle(QString("Jatayu USB Studio v")+studioVersion+" · package revision 21");setWindowIcon(QIcon(":/assets/icon.png"));
        resize(1366,780);setMinimumSize(900,600);
        auto *root=new QWidget;setCentralWidget(root);auto *outer=new QVBoxLayout(root);outer->setContentsMargins(0,0,0,0);outer->setSpacing(0);
        auto *body=new QWidget;auto *horizontal=new QHBoxLayout(body);horizontal->setContentsMargins(0,0,0,0);horizontal->setSpacing(0);
        auto *side=frame("sidebar");side->setFixedWidth(252);auto *sl=column(side,6,12);auto *brand=new QHBoxLayout;
        auto *brandIcon=new QLabel;brandIcon->setPixmap(QPixmap(":/assets/icon.png").scaled(55,55,Qt::KeepAspectRatio,Qt::SmoothTransformation));
        brand->addWidget(brandIcon);brand->addWidget(txt("Jatayu USB\nStudio",16,true,"#60d8ff"),1);
        sl->addLayout(brand);sl->addSpacing(12);
        QStringList icons={"home","usb","copy","trash","shield","refresh","shield","settings","info","download"};
        for(int i=0;i<names.size();++i){
            auto *b=new QPushButton(names[i]);b->setIcon(studioIcon(icons[i]));b->setIconSize(QSize(22,22));b->setObjectName(i==0?"navActive":"nav");b->setFixedHeight(43);b->setToolTip(names[i]);
            sl->addWidget(b);nav<<b;connect(b,&QPushButton::clicked,this,[this,i]{selectPage(i);});
        }
        sl->addStretch();horizontal->addWidget(side);
        pages=new QStackedWidget;pages->setObjectName("pages");horizontal->addWidget(pages,1);outer->addWidget(body,1);
        auto *footer=frame("footer");auto *fl=new QHBoxLayout(footer);fl->setContentsMargins(20,9,20,9);
        fl->addWidget(txt(QString("●  Jatayu USB Studio v")+studioVersion+" · package revision 21",10,true,"#ffffff"));
        status=txt("Ready",10,false,"#dbe7ff");fl->addWidget(status);fl->addStretch();
        backendStatus=txt("Backend: checking...",10,true,"#ffdb81");
        backendStatus->setToolTip("UDisks2 availability does not grant USB access");
        fl->addWidget(backendStatus);fl->addSpacing(16);
        fl->addWidget(txt("JatayuOS   |   jatayuos.in",10,true,"#e4efff"));outer->addWidget(footer);
        // Centralized palette for Studio widgets. The native KDE file chooser
        // must be opened without a styled parent to inherit Plasma colors.
        setStyleSheet(R"CSS(
          QMainWindow, QWidget#pages, QWidget#content, QScrollArea, QScrollArea > QWidget > QWidget { background-color:#0C2043; }
          QFrame#sidebar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0A1B38,stop:1 #263D77); }
          QFrame#footer { background-color:#12274D; }
          QPushButton#nav, QPushButton#navActive { border:0; text-align:left; color:#F5F9FF; font-size:15px; padding:10px 16px; border-radius:11px; background:transparent; }
          QPushButton#nav:hover { background-color:#254C8A; }
          QPushButton#navActive { background-color:#0877EE; color:white; font-weight:700; }
          QFrame#light { background-color:#E0E9FF; color:#142644; border:1px solid #C7D5FA; border-radius:17px; }
          QFrame#workflow { background-color:#142D58; border:1px solid #4772B5; border-radius:17px; }
          QFrame#blue { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #388FEA,stop:1 #0753BD); border:2px solid #8CD8FF; border-radius:16px; }
          QFrame#purple { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #8163EB,stop:1 #4931A9); border:2px solid #BDAAFF; border-radius:16px; }
          QFrame#green { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #29BF90,stop:1 #07846E); border:2px solid #70F9C3; border-radius:16px; }
          QFrame#orange { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F48F18,stop:1 #C35A17); border:2px solid #FFDB81; border-radius:16px; }
          QFrame#teal { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #16B8D8,stop:1 #04719E); border:2px solid #70EAF7; border-radius:16px; }
          QProgressBar { background:#C8D7F5; color:#142644; border:1px solid #A6B9E3; border-radius:7px; text-align:center; } QProgressBar::chunk { background:#0875EA; border-radius:6px; } QFrame#drivePanel { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #233D79,stop:1 #152E60); border:2px solid #668CE0; border-radius:17px; }
          QLineEdit, QComboBox { background-color:#F8FAFF; color:#142644; selection-background-color:#126FE7; selection-color:#FFFFFF; border:1px solid #A6B9E3; border-radius:8px; padding:6px; font-size:12px; min-height:19px; }
          QLineEdit:focus, QComboBox:focus { border:2px solid #1678EF; }
          QLineEdit:disabled, QComboBox:disabled { background-color:#E8EDFA; color:#64748B; }
          QComboBox QAbstractItemView { background-color:#FFFFFF; color:#15233C; selection-background-color:#126FE7; selection-color:#FFFFFF; border:1px solid #7A9DD9; outline:0; padding:2px; }
          QComboBox QAbstractItemView::item { min-height:28px; padding:4px 8px; background-color:#FFFFFF; color:#15233C; }
          QComboBox QAbstractItemView::item:selected { background-color:#126FE7; color:#FFFFFF; }
          QCheckBox { color:#E7F0FF; background:transparent; spacing:7px; }
          QCheckBox:disabled { color:#B8C9E6; }
          QCheckBox::indicator { width:16px; height:16px; }
          QPushButton#primary { background-color:#0875EA; color:#FFFFFF; border:0; border-radius:9px; padding:9px; font-size:14px; font-weight:bold; }
          QPushButton#primary:hover { background-color:#248DFF; }
          QPushButton#secondary { background-color:#EAF0FF; color:#142644; border:1px solid #A7B8DD; border-radius:8px; padding:8px; }
          QPushButton#secondary:hover { background-color:#D5E3FF; }
          QToolTip { background-color:#F8FAFF; color:#142644; border:1px solid #9FB4E2; }
        )CSS");
        pages->addWidget(home());
        for(int i=1;i<names.size();++i)pages->addWidget(i==6?safetyPage():otherPage(i));
        connect(&refreshTimer,&QTimer::timeout,this,&Studio::refreshDrives);if(preferences.value("devices/autoRefresh",true).toBool())refreshTimer.start(2500);refreshDrives();
        connect(&backendTimer,&QTimer::timeout,this,&Studio::probeBackend);
        backendTimer.start(5000);probeBackend();
    }
    ~Studio() override {
        refreshTimer.stop();
        backendTimer.stop();
        for(auto *process:findChildren<QProcess *>()){
            process->disconnect();
            if(process->state()!=QProcess::NotRunning){
                process->kill();
                process->waitForFinished(1000);
            }
        }
    }
protected:
    void closeEvent(QCloseEvent *event) override {
        if(operation)event->ignore();
        else QMainWindow::closeEvent(event);
    }
private:
    QString backendFile(const QString &name) const {
        const QString installed=QDir(QCoreApplication::applicationDirPath()).filePath("../lib/jatayu-usb-studio/"+name);
        if(QFileInfo::exists(installed))return installed;
        const QString local=QDir(QCoreApplication::applicationDirPath()).filePath("backend/"+name);
        if(QFileInfo::exists(local))return local;
        return "/usr/lib/jatayu-usb-studio/"+name;
    }
    bool confirmErase(const QString &path,const QString &details,const QString &action="ERASE"){
        if(path.isEmpty())return false;
        const QString expected=action+" "+path;
        QDialog dialog(this);
        dialog.setWindowTitle("Confirm USB operation");
        auto *layout=new QVBoxLayout(&dialog);
        auto *instructions=new QLabel(details+"\n\nType exactly: "+expected);
        instructions->setTextFormat(Qt::PlainText);
        instructions->setWordWrap(true);
        auto *typed=new QLineEdit;
        typed->setAccessibleName("Type "+expected+" to confirm");
        auto *hint=new QLabel;
        hint->setTextFormat(Qt::PlainText);
        hint->setWordWrap(true);
        auto *buttons=new QDialogButtonBox(QDialogButtonBox::Ok|QDialogButtonBox::Cancel);
        layout->addWidget(instructions);
        layout->addWidget(typed);
        layout->addWidget(hint);
        layout->addWidget(buttons);
        connect(buttons,&QDialogButtonBox::accepted,&dialog,[&dialog,typed,hint,expected]{
            if(typed->text()==expected){dialog.accept();return;}
            hint->setText("The confirmation does not match. Type "+expected+" exactly. No changes have been made.");
            typed->setFocus();
            typed->selectAll();
        });
        connect(buttons,&QDialogButtonBox::rejected,&dialog,&QDialog::reject);
        typed->setFocus();
        return dialog.exec()==QDialog::Accepted;
    }
    void runOperation(const QString &title,const QStringList &arguments,const QStringList &expected,
                      std::function<void(const QJsonObject &)> onSuccess={}){
        if(operation){QMessageBox::warning(this,title,"Wait for the current operation to finish.");return;}
        const QString script=backendFile("studio_operations.py");
        auto marker=std::make_shared<QTemporaryDir>();
        if(!QFileInfo(script).isFile() || !marker->isValid()){
            QMessageBox::warning(this,title,"The operation backend or private cancellation directory is unavailable.");return;
        }
        auto *dialog=new QDialog(this);
        dialog->setWindowTitle(title);
        dialog->setWindowModality(Qt::WindowModal);
        dialog->resize(690,270);
        auto *layout=new QVBoxLayout(dialog);
        auto *message=new QLabel("Checking the selection…");
        message->setTextFormat(Qt::PlainText);
        message->setWordWrap(true);
        message->setTextInteractionFlags(Qt::TextSelectableByMouse);
        auto *log=new QPlainTextEdit;
        log->setReadOnly(true);
        log->setMaximumBlockCount(80);
        auto *bar=new QProgressBar;
        bar->setRange(0,0);
        auto *cancel=new QPushButton("Cancel");
        layout->addWidget(message);layout->addWidget(bar);layout->addWidget(log);layout->addWidget(cancel);
        operation=new QProcess(dialog);
        auto *process=operation;
        const QString cancelPath=marker->filePath("cancel");
        auto cancelling=std::make_shared<bool>(false);
        connect(cancel,&QPushButton::clicked,dialog,[message,cancel,cancelPath,cancelling]{
            QFile request(cancelPath);
            if(request.open(QIODevice::WriteOnly|QIODevice::NewOnly)){
                cancel->setEnabled(false);
                *cancelling=true;
                message->setText("Stopping. Waiting for any pending USB writes to finish. Keep the drive connected.");
            }else message->setText("Could not request cancellation.");
        });
        connect(dialog,&QDialog::finished,dialog,[dialog,process](int){
            if(process->state()==QProcess::NotRunning)dialog->deleteLater();
            else QTimer::singleShot(0,dialog,[dialog]{dialog->show();});
        });
        auto result=std::make_shared<QJsonObject>();
        auto error=std::make_shared<QString>();
        auto phase=std::make_shared<QString>();
        auto consume=[dialog,process,message,bar,log,result,error,phase,cancelling]{
            while(process->canReadLine()){
                const auto obj=QJsonDocument::fromJson(process->readLine()).object();
                const QString event=obj.value("event").toString();
                if(event=="progress"){
                    const QString next=obj.value("phase").toString();
                    if(next!=*phase){*phase=next;log->appendPlainText(next);}
                    const double done=obj.value("bytes").toDouble(), total=obj.value("total").toDouble();
                    bar->setRange(0,total>0?100:0);
                    if(total>0)bar->setValue(int(std::clamp(done/total*100.0,0.0,100.0)));
                    QString summary=next+" · "+QString::number(obj.value("elapsed").toDouble(),'f',1)+" s elapsed";
                    if(done>0)summary+=" · "+sizeText(quint64(obj.value("speed").toDouble()))+"/s";
                    if(obj.value("remaining").isDouble())summary+=" · "+QString::number(obj.value("remaining").toDouble(),'f',0)+" s remaining";
                    if(!*cancelling)message->setText(summary);
                }else if(event=="confirm_write"){
                    if(*cancelling){process->write("CANCEL\n");process->closeWriteChannel();continue;}
                    const QString device=obj.value("device").toString();
                    log->appendPlainText("Authorization obtained. Waiting for final confirmation for "+device+".");
                    const auto decision=QMessageBox::warning(dialog,"Write to USB now?",
                        "The prepared operation will overwrite data on "+device+". Continue?",
                        QMessageBox::Yes|QMessageBox::No,QMessageBox::No);
                    process->write(decision==QMessageBox::Yes?"WRITE\n":"CANCEL\n");
                    process->closeWriteChannel();
                }else if(event=="error")*error=obj.value("message").toString();
                else if(event=="result")*result=obj;
            }
        };
        connect(process,&QProcess::readyReadStandardOutput,dialog,consume);
        const auto finish=[this,dialog,process,message,bar,log,cancel,marker,result,error,phase,expected,onSuccess,consume,arguments](bool exited){
            consume();
            operation=nullptr;
            const QString state=result->value("status").toString();
            const QString digest=result->value("sha256").toString();
            const bool needsDigest=state=="WRITTEN_AND_VERIFIED" || state=="IMAGE_MATCH" || state=="DOWNLOADED";
            const bool succeeded=exited && expected.contains(state) && (!needsDigest ||
                (QRegularExpression("^[0-9a-f]{64}$").match(digest).hasMatch() && result->value("bytes").toDouble()>0));
            const bool findings=state=="FILESYSTEM_FINDINGS";
            QString detail;
            if(!succeeded){
                const bool cancelled=state=="CANCELLED";
                detail=cancelled?"Operation cancelled. ":"Operation failed. ";
                if(!phase->isEmpty())detail+="Last stage: "+*phase+". ";
                detail+=(*error).left(1200);
                const auto diagnostics=QString::fromUtf8(process->readAllStandardError()).trimmed().left(500);
                if(!diagnostics.isEmpty())log->appendPlainText(diagnostics);
                if(!cancelled && *phase!="Staging ISO" && *phase!="Checking image compatibility" && *phase!="Preparing filesystem snapshot" && *phase!="Reading filesystem snapshot" && (arguments[0]=="write" || arguments[0]=="clone" || arguments[0]=="repair" || arguments[0]=="format"))
                    detail+=" If writing had started, the USB may be partially overwritten.";
                if(!cancelled && arguments[0]=="windows" &&
                   (*phase=="write" || *phase=="verify" || *phase=="Clearing old partition metadata" ||
                    *phase=="Verifying cleared partition metadata"))
                    detail+=" The USB may be partially overwritten.";
            }else if(state=="WRITTEN_AND_VERIFIED" && arguments[0]=="windows"){
                detail="Windows installer written. SHA-256 readback of the prepared FAT32 image matched. Bootability was not tested.";
            }else if(state=="WRITTEN_AND_VERIFIED"){
                detail=arguments[0]=="write"
                    ?"Image written and verified. SHA-256 readback matched. Bootability was not tested."
                    :"Written and SHA-256 readback matched.";
            }
            else if(state=="QUICK_FORMAT_VERIFIED")detail="Quick FAT32 format complete. Filesystem metadata passed readback verification.";
            else if(state=="IMAGE_MATCH")detail="USB image prefix matches the ISO.";
            else if(state=="DOWNLOADED")detail="ISO saved.";
            else if(state=="SAFETY_CHECKED")detail="Live device safety checks passed.";
            else detail=findings?"Filesystem check reported problems.":"Filesystem check passed.";
            if(succeeded && !digest.isEmpty())detail+="\nSHA-256 "+digest;
            if(succeeded && !result->value("message").toString().isEmpty())log->appendPlainText(result->value("message").toString());
            log->appendPlainText(detail);
            message->setText(detail);
            const int lastProgress=bar->maximum()>0?bar->value():0;
            bar->setRange(0,100);bar->setValue(succeeded && !findings?100:(state=="CANCELLED"?std::max(0,lastProgress):0));
            cancel->disconnect();
            cancel->setEnabled(true);cancel->setText("Close");
            connect(cancel,&QPushButton::clicked,dialog,&QDialog::accept);
            if(succeeded && onSuccess)onSuccess(*result);
            refreshDrives();
        };
        connect(process,QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),dialog,
                [finish](int code,QProcess::ExitStatus exit){finish(code==0 && exit==QProcess::NormalExit);});
        connect(process,&QProcess::errorOccurred,dialog,[finish,error](QProcess::ProcessError code){
            if(code==QProcess::FailedToStart){*error="Unable to start the operation backend.";finish(false);}
        });
        dialog->show();
        process->start("/usr/bin/python3",QStringList{"-B","-E","-s",script}+arguments+QStringList{"--cancel-file",cancelPath});
    }
    QStringList selectionArguments(QComboBox *selection,bool source=false) {
        const QString device=selection->currentData().toString();
        const QString sequence=selection->currentData(Qt::UserRole+2).toString();
        if(device.isEmpty() || sequence.isEmpty())return {};
        return {source?"--source":"--device",device,source?"--source-sequence":"--sequence",sequence};
    }
    QComboBox *cloneSource=nullptr, *cloneDestination=nullptr;
    QPushButton *cloneStart=nullptr;
#ifdef JATAYU_UI_TEST
    friend int testStudioNavigation(QApplication &);
#endif
    void populateOperationChoice(QComboBox *box, const QString &excluded={}) {
        const QSignalBlocker blocker(box);
        const bool filesystemPicker=box->property("partitions").toBool();
        const QString previous=box->currentData().toString();
        const QString previousSequence=box->currentData(Qt::UserRole+2).toString();
        const QString previousPartition=box->currentData(Qt::UserRole+3).toString();
        box->clear();
        box->addItem(filesystemPicker?"Select a USB partition or filesystem":"Select a removable USB drive");
        for(const auto &drive:devices){
            if(drive.sequence.isEmpty() || drive.path==excluded)continue;
            QList<Partition> entries=filesystemPicker?drive.partitions:QList<Partition>();
            if(entries.isEmpty())entries.append({drive.path,drive.filesystem,drive.bytes});
            for(const auto &entry:entries){
                if(entry.path.isEmpty())continue;
                const QString label=filesystemPicker
                    ? (entry.path==drive.path?QString("Whole-drive filesystem "):QString("Partition "))+entry.path+" on "+drive.name+" ("+sizeText(entry.bytes)+") · "+
                      (entry.fs.isEmpty()?QString("Unknown filesystem"):entry.fs)
                    : drive.detail;
                box->addItem(label,drive.path);
                const int index=box->count()-1;
                box->setItemData(index,QVariant::fromValue<qulonglong>(entry.bytes),Qt::UserRole+1);
                box->setItemData(index,drive.sequence,Qt::UserRole+2);
                box->setItemData(index,entry.path,Qt::UserRole+3);
                box->setItemData(index,entry.fs,Qt::UserRole+4);
                if(drive.path==previous && drive.sequence==previousSequence && entry.path==previousPartition)
                    box->setCurrentIndex(index);
            }
        }
    }
    void updateCloneAction(){
        const auto source=selectionArguments(cloneSource,true);
        const auto destination=selectionArguments(cloneDestination);
        cloneStart->setEnabled(!source.isEmpty() && !destination.isEmpty() && source[1]!=destination[1]
            && cloneDestination->currentData(Qt::UserRole+1).toULongLong()>=cloneSource->currentData(Qt::UserRole+1).toULongLong());
    }
    void populateCloneDestination(){
        const QString source=cloneSource->currentData().toString();
        if(cloneDestination->view()->isVisible())cloneDestination->hidePopup();
        populateOperationChoice(cloneDestination,source);
        if(cloneDestination->count()==1)cloneDestination->setItemText(0,"Connect a second USB drive to clone");
        cloneDestination->setEnabled(cloneDestination->count()>1);
        updateCloneAction();
    }
    void populateOperationChoices(){
        const QString previousSource=cloneSource?cloneSource->currentData().toString():QString();
        for(auto *box:operationChoices)
            if(box!=cloneDestination && !box->view()->isVisible())populateOperationChoice(box);
        if(cloneDestination && (!cloneDestination->view()->isVisible() || cloneSource->currentData().toString()!=previousSource))
            populateCloneDestination();
    }
    QComboBox *operationPicker(QVBoxLayout *layout,bool partitions=false){
        auto *box=new QComboBox;
        box->setProperty("partitions",partitions);
        layout->addWidget(box);
        operationChoices<<box;
        return box;
    }
    void setBackendStatus(const QString &message,const QString &color){
        if(!backendStatus)return;
        backendStatus->setText(message);
        backendStatus->setStyleSheet("color:"+color+";background:transparent;");
    }
    void probeUdisksFallback(){
        // UDisks2 availability is independent of the optional Jatayu inspection service.
        // Never interpret this read-only probe as authorization to write.
        auto *probe=new QProcess(this);
        probe->setProgram("busctl");
        probe->setArguments({"--system","--timeout=3s","get-property",
            "org.freedesktop.UDisks2","/org/freedesktop/UDisks2/Manager",
            "org.freedesktop.UDisks2.Manager","Version"});
        auto *timer=new QTimer(probe);timer->setSingleShot(true);
        connect(timer,&QTimer::timeout,probe,[probe]{
            if(probe->state()!=QProcess::NotRunning)probe->kill();
        });
        connect(probe,&QProcess::finished,this,[this,probe](int code,QProcess::ExitStatus status){
            const bool available=(code==0 && status==QProcess::NormalExit &&
                                  !probe->readAllStandardOutput().trimmed().isEmpty());
            setBackendStatus(available?"UDisks2: reachable":
                "Backend: unavailable / unverified",available?"#ffdb81":"#ffdb81");
            if(backendStatus)backendStatus->setToolTip(available?
                "UDisks2 is reachable. USB operations request authorization separately.":
                "Neither the Jatayu inspection service nor the UDisks2 manager could be verified.");
            probe->deleteLater();
        });
        probe->start();timer->start(4000);
    }
    void probeBackend(){
        if(backendProbe)return; // Never overlap polls.
        auto *proc=new QProcess(this);backendProbe=proc;
        proc->setProgram("busctl");
        proc->setArguments({"--system","--timeout=3s","call",
            "in.jatayuos.USBStudio.Inspection","/in/jatayuos/USBStudio/Inspection",
            "in.jatayuos.USBStudio.Inspection1","Capabilities"});
        // The process is read-only; no start, installation, authorization or writing.
        auto *timeout=new QTimer(proc);timeout->setSingleShot(true);
        connect(timeout,&QTimer::timeout,proc,[proc]{if(proc->state()!=QProcess::NotRunning)proc->kill();});
        connect(proc,&QProcess::finished,this,[this,proc](int code,QProcess::ExitStatus exit){
            if(backendProbe!=proc)return;
            const QString output=QString::fromUtf8(proc->readAllStandardOutput()).trimmed();
            // busctl encodes the single string as: s "{\"writing_enabled\":false,...}"
            bool valid=false;
            if(code==0 && exit==QProcess::NormalExit && output.startsWith("s ")){
                const QString quoted=output.mid(2).trimmed();
                // QJsonDocument parses the quoted D-Bus string as a JSON string.
                QJsonParseError err;
                const auto decoded=QJsonDocument::fromJson(("["+quoted+"]").toUtf8(),&err);
                if(err.error==QJsonParseError::NoError && decoded.isArray() && decoded.array().size()==1){
                    const auto payload=QJsonDocument::fromJson(decoded.array().at(0).toString().toUtf8());
                    const auto obj=payload.object();
                    valid=payload.isObject() && obj.value("writing_enabled").isBool()
                        && !obj.value("writing_enabled").toBool()
                        && obj.value("authorized").isBool() && !obj.value("authorized").toBool()
                        && obj.value("service_mode").toString()=="inspection_only";
                }
            }
            if(valid)setBackendStatus("Backend: inspection connected · read-only","#70F9C3");
            else probeUdisksFallback();
            if(backendStatus)backendStatus->setToolTip(valid?
                "Real system D-Bus inspection service responded with writing disabled. This is not write authorization.":
                "Service unavailable, timed out, or returned an untrusted response. Check: systemctl status jatayu-usb-inspection.service");
            backendProbe=nullptr;proc->deleteLater();
        });
        connect(proc,&QProcess::errorOccurred,this,[this,proc](QProcess::ProcessError){
            if(backendProbe==proc){
                probeUdisksFallback();
                backendProbe=nullptr;proc->deleteLater();
            }
        });
        proc->start();timeout->start(4000);
    }
    QWidget* wrapPage(QWidget *inner){
        auto *sc=new QScrollArea;sc->setWidgetResizable(true);sc->setFrameShape(QFrame::NoFrame);sc->setWidget(inner);return sc;
    }
    void selectPage(int index){
        pages->setCurrentIndex(index);
        for(int i=0;i<nav.size();++i){nav[i]->setObjectName(i==index?"navActive":"nav");nav[i]->style()->unpolish(nav[i]);nav[i]->style()->polish(nav[i]);}
        if(index==0||index==1||index==6)refreshDrives();
    }
    QWidget* home(){
        auto *w=new QWidget;w->setObjectName("content");auto *v=column(w,7,12);
        auto *banner=new Banner;auto *bv=column(banner,8,27);
        bv->addWidget(txt("Jatayu USB Studio",30,true,"#ffffff"));
        bv->addWidget(txt("Your complete USB management workspace",14,true,"#e3f2ff"));
        bv->addWidget(txt("Create Bootable USB   •   Clone   •   Format   •   Verify",10,false,"#d2e8ff"));
        bv->addStretch();v->addWidget(banner);
        auto *work=new QWidget;auto *wh=new QHBoxLayout(work);wh->setContentsMargins(0,0,0,0);wh->setSpacing(12);
        auto *left=new QWidget;auto *lv=column(left,7,0);
        lv->addWidget(txt("USB Tools",21,true,"white"));lv->addWidget(txt("Choose a task to get started",11,false,"#c7d9f8"));
        auto *grid=new QWidget;auto *g=new QGridLayout(grid);g->setContentsMargins(0,0,0,0);g->setSpacing(12);
        QStringList titles={"Create Bootable USB","Clone USB","Format USB","Verify USB","USB Repair"};
        QStringList subtitles={"Create bootable media from an ISO","Copy one USB drive to another","Erase and format a USB drive","Check USB image integrity","Diagnose USB drive issues safely"};
        QStringList symbols={"usb","copy","trash","shield","refresh"};
        QStringList colors={"blue","purple","green","orange","teal"};
        for(int i=0;i<5;++i){
            auto *card=frame(colors[i]);card->setMinimumHeight(138);card->setMaximumHeight(150);card->setCursor(Qt::PointingHandCursor);
            auto *cl=column(card,5,12);
            auto *top=new QHBoxLayout;auto *icon=new QLabel;icon->setPixmap(studioIcon(symbols[i]).pixmap(36,36));top->addWidget(icon);top->addStretch();
            auto *arrow=new QLabel;arrow->setPixmap(studioIcon("chevron").pixmap(22,22));top->addWidget(arrow);cl->addLayout(top);
            cl->addWidget(txt(titles[i],12,true,"white"));cl->addWidget(txt(subtitles[i],10,false,"#f4f8ff"));cl->addStretch();
            card->setProperty("destination",i+1);card->installEventFilter(this);
            for(auto *label:card->findChildren<QLabel*>()){label->setAttribute(Qt::WA_TransparentForMouseEvents);}
            g->addWidget(card,i/3,i%3);
        }
        lv->addWidget(grid,0);lv->addStretch();wh->addWidget(left,5);
        auto *right=frame("drivePanel");right->setMinimumWidth(330);auto *rv=column(right,7,12);
        auto *head=new QHBoxLayout;head->addWidget(txt("Detected USB Drive",17,true,"white"));head->addStretch();
        auto *refreshIcon=new QPushButton;refreshIcon->setIcon(studioIcon("refresh"));refreshIcon->setIconSize(QSize(20,20));refreshIcon->setFixedSize(38,38);refreshIcon->setObjectName("nav");head->addWidget(refreshIcon);rv->addLayout(head);
        connect(refreshIcon,&QPushButton::clicked,this,&Studio::refreshDrives);
        deviceInfo=txt("Scanning connected USB drives…",11,false,"#e3efff");deviceInfo->setTextInteractionFlags(Qt::TextSelectableByMouse);rv->addWidget(deviceInfo);
        auto *refresh=new QPushButton("USB Details / Refresh");refresh->setObjectName("secondary");rv->addWidget(refresh);
        connect(refresh,&QPushButton::clicked,this,&Studio::refreshDrives);
        rv->addWidget(txt("DEVICE SAFETY",10,true,"#d7e7ff"));
        identityStatus=txt("INSPECTING  •  Waiting for first device scan",11,true,"#ffd88a");
        identityStatus->setWordWrap(true);rv->addWidget(identityStatus);
        auto *resetIdentity=new QPushButton("Capture new identity baseline (read-only)");
        resetIdentity->setObjectName("secondary");rv->addWidget(resetIdentity);
        connect(resetIdentity,&QPushButton::clicked,this,[this]{
            if(QMessageBox::warning(this,"Replace device baseline",
                identityAlert ? "The current device has an identity warning. Confirm this is the intended USB before replacing the advisory baseline. Capturing an advisory baseline does not modify the USB." : "The current USB already matches its baseline. Capture a fresh advisory baseline anyway? Capturing an advisory baseline does not modify the USB.",
                QMessageBox::Cancel|QMessageBox::Ok,QMessageBox::Cancel)==QMessageBox::Ok){
                baselineRequested=true;refreshDrives();
            }
        });
        auto *detailsPage=new QPushButton("Open Device Safety details");detailsPage->setObjectName("secondary");rv->addWidget(detailsPage);
        connect(detailsPage,&QPushButton::clicked,this,[this]{selectPage(6);});
        rv->addWidget(txt("USB-transport disks only. Identity status is advisory, never write authorization.",9,false,"#b8ccec"));
        rv->addWidget(txt("Device inspection is read-only",10,true,"#76f5ba"));rv->addStretch();wh->addWidget(right,4);
        v->addWidget(work,1);return wrapPage(w);
    }
    QWidget* safetyPage(){
        auto *w=new QWidget;w->setObjectName("content");auto *v=column(w,12,16);
        v->addWidget(txt("Device Safety",24,true,"white"));
        v->addWidget(txt("Read-only USB identity, topology and mount information. No write authorization is possible.",12,false,"#dbe7ff"));
        auto *panel=frame("drivePanel");auto *pv=column(panel,12,18);
        pv->addWidget(txt("USB identity inspection",18,true,"white"));
        safetySummary=txt("INSPECTING — Waiting for a device scan",12,true,"#ffd88a");pv->addWidget(safetySummary);
        safetyDetails=txt("Refreshing removable USB information…",11,false,"#e3efff");
        safetyDetails->setTextInteractionFlags(Qt::TextSelectableByMouse);safetyDetails->setWordWrap(true);pv->addWidget(safetyDetails);
        auto *buttons=new QHBoxLayout;
        auto *refresh=new QPushButton("Refresh USB inspection");refresh->setObjectName("secondary");buttons->addWidget(refresh);
        connect(refresh,&QPushButton::clicked,this,&Studio::refreshDrives);
        auto *rebaseline=new QPushButton("Capture new advisory baseline");rebaseline->setObjectName("secondary");buttons->addWidget(rebaseline);
        connect(rebaseline,&QPushButton::clicked,this,[this]{
            auto choice=QMessageBox::warning(this,"Replace device baseline",
                identityAlert ? "A device identity warning is active. Confirm that the connected USB is the intended device before capturing a new advisory baseline. No disk writes will be enabled." : "The USB currently matches its baseline. Replace the advisory baseline anyway? No disk writes will be enabled.",
                QMessageBox::Cancel|QMessageBox::Ok,QMessageBox::Cancel);
            if(choice==QMessageBox::Ok){baselineRequested=true;refreshDrives();}
        });
        pv->addLayout(buttons);
        pv->addWidget(txt("To capture a baseline, first select the intended target on Create Bootable USB. For troubleshooting, see About → FAQ.",10,false,"#b8ccec"));
        pv->addWidget(txt("INTEGRATED STORAGE INSPECTION (ADVISORY)",11,true,"#d7e7ff"));
        auto *safetyTarget=operationPicker(pv);
        auto *runIntegrated=new QPushButton("Run integrated read-only inspection");
        runIntegrated->setObjectName("secondary");pv->addWidget(runIntegrated);
        connect(runIntegrated,&QPushButton::clicked,this,[this,safetyTarget]{
            const auto selection=selectionArguments(safetyTarget);
            if(selection.isEmpty()){QMessageBox::warning(this,"Device Safety","Select a removable USB drive with a known disk generation.");return;}
            runOperation("Device Safety",QStringList{"inspect"}+selection,{"SAFETY_CHECKED"});
        });
        pv->addWidget(txt("Checks USB identity, mount state, read-only status, active swap and kernel holders. Authorization is requested separately by operations that access a USB.",10,false,"#b8ccec"));
        pv->addWidget(txt("DEVICE SAFETY EVENT HISTORY",11,true,"#d7e7ff"));
        auto *historyToolbar=new QHBoxLayout;
        historyToolbar->addWidget(txt("Current session · most recent first",10,false,"#b8ccec"));
        historyToolbar->addStretch();
        eventFilterChoice=new QComboBox;
        eventFilterChoice->setMinimumWidth(145);
        eventFilterChoice->setAccessibleName("Filter safety events");
        eventFilterChoice->addItem("All events","all");
        eventFilterChoice->addItem("Information","info");
        eventFilterChoice->addItem("Warnings","warning");
        eventFilterChoice->addItem("Critical","critical");
        historyToolbar->addWidget(eventFilterChoice);
        auto *exportButton=new QPushButton("Export history (.txt)");
        exportButton->setObjectName("secondary");
        historyToolbar->addWidget(exportButton);
        pv->addLayout(historyToolbar);
        connect(eventFilterChoice,QOverload<int>::of(&QComboBox::currentIndexChanged),this,[this](int){renderSafetyEvents();});
        connect(exportButton,&QPushButton::clicked,this,[this]{exportSafetyEvents();});
        eventHistory=txt("Waiting for the first USB inspection…",10,false,"#dbe7ff");
        eventHistory->setWordWrap(true);eventHistory->setTextInteractionFlags(Qt::TextSelectableByMouse);
        pv->addWidget(eventHistory);
        pv->addWidget(txt("A matching identity is NOT permission to write. USB serials can be duplicated; device paths may change. Each operation independently checks the live device.",10,false,"#b8ccec"));
        v->addWidget(panel);v->addStretch();return wrapPage(w);
    }
    QWidget *aboutPage(){
        auto *page=new QWidget;
        page->setObjectName("content");
        auto *layout=column(page,18,20);
        auto *hero=frame("aboutHero");
        hero->setStyleSheet(R"(
            QFrame#aboutHero {
                border:1px solid #36588A; border-radius:18px;
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #14233F,stop:0.68 #192F51,stop:1 #204372);
            }
            QPushButton#aboutWebsite {
                color:#FFFFFF; background:#106ED3; border:1px solid #65ACFF;
                border-radius:8px; padding:8px 14px; font-weight:600;
            }
            QPushButton#aboutWebsite:hover, QPushButton#aboutWebsite:focus { background:#185BA5; }
        )");
        auto *header=new QHBoxLayout(hero);
        header->setContentsMargins(26,20,26,20);
        header->setSpacing(20);
        auto *icon=new QLabel;
        icon->setPixmap(QIcon(":/assets/icon.png").pixmap(72,72));
        header->addWidget(icon,0,Qt::AlignTop);
        auto *identity=new QVBoxLayout;
        identity->setSpacing(6);
        identity->addWidget(txt("Jatayu USB Studio",26,true,"#FFFFFF"));
        identity->addWidget(txt("Create, verify and manage USB media on JatayuOS.",11,false,"#D9E8FF"));
        identity->addWidget(txt("Created by Anup Kumar Yadav",11,true,"#FFFFFF"));
        identity->addWidget(txt(QString(studioVersion)+" · Package revision 21 · Debian 13 / KDE Plasma 6",10,false,"#D9E8FF"));
        auto *website=new QPushButton("Visit jatayuos.in");
        website->setObjectName("aboutWebsite");
        identity->addWidget(website,0,Qt::AlignLeft);
        connect(website,&QPushButton::clicked,this,[]{QDesktopServices::openUrl(QUrl("https://jatayuos.in"));});
        header->addLayout(identity,1);
        layout->addWidget(hero);

        auto *help=new QTabWidget;
        help->setAccessibleName("Jatayu USB Studio help");
        help->setStyleSheet(R"(
            QTabWidget::pane { background:#101F38; border:1px solid #304B73; border-radius:12px; }
            QTabBar::tab { color:#B7CAE8; background:#142640; padding:10px 20px;
                          margin-right:6px; border:1px solid #304B73; border-radius:8px; }
            QTabBar::tab:selected { color:#F4F9FF; background:#224575; border-color:#5B9DF5; font-weight:600; }
            QTabBar::tab:hover { color:#FFFFFF; border-color:#5B9DF5; }
            QTabBar::tab:focus { border:2px solid #8CE1FF; }
            QScrollArea#aboutScroll { background:#101F38; border:0; }
            QScrollArea#aboutScroll QWidget#aboutTabBody { background:#101F38; }
            QFrame#aboutHelpEntry { background:#192D4B; border:1px solid #334F76;
                                    border-left:3px solid #64AFFF; border-radius:10px; }
        )");
        auto addHelpTab=[help](const QString &title){
            auto *scroll=new QScrollArea;
            scroll->setObjectName("aboutScroll");
            scroll->setWidgetResizable(true);
            scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
            auto *body=new QWidget;
            body->setObjectName("aboutTabBody");
            auto *rows=column(body,12,18);
            scroll->setWidget(body);
            help->addTab(scroll,title);
            return rows;
        };
        auto addEntry=[](QVBoxLayout *rows,const QString &title,const QString &description){
            auto *entry=frame("aboutHelpEntry");
            auto *content=column(entry,7,15);
            content->addWidget(txt(title,13,true,"#F0F6FF"));
            auto *body=txt(description,11,false,"#CADAF0");
            body->setTextInteractionFlags(Qt::TextSelectableByMouse);
            content->addWidget(body);
            rows->addWidget(entry);
        };
        auto *overview=addHelpTab("About this tool");
        addEntry(overview,"What Jatayu USB Studio does","Jatayu USB Studio is a desktop tool for creating bootable Linux USB drives and managing removable storage. It brings ISO downloads, checksums, raw USB cloning, formatting and filesystem diagnostics into one app. It is designed to run as a regular desktop user and requests storage access through UDisks2.");
        addEntry(overview,"Choose the right job","Use Create Bootable USB to write an installer. Use Format USB to prepare a drive for ordinary file storage. Use Verify USB to check an image or compare a previously written drive with its source ISO. Use USB Repair to investigate filesystem errors.");
        addEntry(overview,"Before you change a drive","Back up important files and check the drive model, capacity and device path. Unmount its filesystems before working on it. Writing an ISO, cloning to a drive and formatting can erase the destination. Read both confirmations before proceeding.");
        overview->addStretch();

        auto *guide=addHelpTab("How to use");
        auto *jump=new QComboBox;
        jump->setAccessibleName("Jump to a guide topic");
        jump->addItem("Jump to a guide topic…");
        guide->addWidget(jump);
        addEntry(guide,"Home",
            "1. Connect your USB drive and check its model, capacity and device path.\n"
            "2. Click USB Details / Refresh if the device list is out of date.\n"
            "3. Use a tool shortcut or the sidebar to open the operation you need.");
        addEntry(guide,"Create Bootable USB",
            "1. Click Browse and select a hybrid Linux ISO or a Windows x64 installer ISO. You can compare its SHA-256 with the publisher’s checksum in Verify USB.\n"
            "2. Select the target USB by model and capacity. Unmount its filesystems. Inspect USB Write Safety can check for blockers.\n"
            "3. Use Write hybrid Linux ISO for Linux or Create Windows installer (UEFI) for Windows. Type the exact confirmation shown, approve any system authorization and confirm the actual write. The destination will be erased.\n"
            "4. Wait for the write and SHA-256 readback to finish before removing the drive. To test booting, select the USB in your computer’s boot menu.");
        addEntry(guide,"Advanced diagnostics",
            "Open Settings → Developer Tools and choose an ISO. Simulate USB Writing checks the selected image and drive without writing. Copy ISO to new file tests copy progress and verification using a regular file. It needs space for the copied ISO and leaves the USB untouched.");
        addEntry(guide,"Clone USB",
            "1. Connect two separate USB drives and unmount their filesystems.\n"
            "2. Pick the source first, then a destination at least as large as the entire source device. Check both models and paths.\n"
            "3. Click Clone USB and follow the prompts. The destination’s existing contents will be erased. Wait for the copy and readback verification to complete.");
        addEntry(guide,"Format USB",
            "1. Select and unmount the target USB. Choose FAT32 for broad compatibility, exFAT for large files shared across modern systems, NTFS for Windows-oriented storage or ext4 for Linux storage. FAT32 cannot store a single file of 4 GiB or larger.\n"
            "2. For FAT32, leave Full format unchecked for a quicker format. Old data may remain recoverable. Full format overwrites and verifies the whole device and takes longer. Other filesystems currently use full format.\n"
            "3. Click Format USB and confirm after reviewing the destination. Wait for completion before using the drive.");
        addEntry(guide,"Verify USB",
            "1. Select the ISO. To check the download, paste a trusted SHA-256 value or choose a checksum file, then click Calculate / Verify SHA-256. MATCH means the ISO agrees with that reference. Get the reference from a source you trust.\n"
            "2. To check a USB written from that same ISO, unmount it, pick the USB and click Verify written USB against ISO. The app reads the image-length portion of the drive. A mismatch is expected after formatting the drive or writing another image.");
        addEntry(guide,"USB Repair",
            "1. Unmount all filesystems on the drive and select the affected partition or whole-drive filesystem.\n"
            "2. Start with Check filesystem health. It is read-only and uses UDisks2 directly when supported. A fallback check may need temporary space equal to the selected filesystem.\n"
            "3. If problems are reported, back up readable files before using Repair filesystem. Automatic repair supports FAT, exFAT and ext4. NTFS has a limited read-only check. Repair works on a temporary copy and needs space equal to the selected filesystem. If the check passes, skip repair.");
        addEntry(guide,"Device Safety",
            "Review the drive identity and topology. Use Refresh USB inspection or select a drive and run the integrated read-only inspection to see blockers such as mounts or active swap. Capture new advisory baseline only after confirming the intended hardware. The baseline helps flag changes. You can export the inspection history as a text file.");
        addEntry(guide,"Settings",
            "Automatic refresh updates the USB list every 2.5 seconds and remembers your choice. If you turn it off, use Refresh USB devices now after connecting or disconnecting a drive.");
        addEntry(guide,"Downloads",
            "1. Paste an HTTPS link to a Linux ISO and choose a destination folder.\n"
            "2. Click Download ISO and wait for the download and SHA-256 calculation. Compare the digest with the publisher’s trusted value if available.\n"
            "3. Click Use downloaded ISO to load the file in Create Bootable USB. Review the target there before starting a write.");
        auto *guideScroll=qobject_cast<QScrollArea *>(help->widget(1));
        for(int i=1;i<guide->count();++i){
            auto *entry=guide->itemAt(i)->widget();
            jump->addItem(entry->findChild<QLabel *>()->text());
        }
        connect(jump,&QComboBox::activated,guideScroll,[guide,guideScroll,jump](int index){
            if(index>0)guideScroll->ensureWidgetVisible(guide->itemAt(index)->widget(),0,16);
            jump->setCurrentIndex(0);
        });
        guide->addStretch();
        auto *faq=addHelpTab("FAQ");
        addEntry(faq,"Why do I see two entries for one USB drive?","USB Repair lists individual filesystems. For example, /dev/sdb1 and /dev/sdb2 can belong to the same /dev/sdb drive.");
        addEntry(faq,"Why is my USB blocked?","Open Device Safety for the reason. Mounted filesystems, active swap or a changed device identity can prevent access. Run as a regular desktop user and respond to the system authorization prompt when it appears.");
        addEntry(faq,"Why does Device Safety warn after I reconnect my USB?",
            "Reconnecting a drive clears the warning when its identity and layout match the saved baseline at the same device path. If the warning remains, check the drive model, capacity and path before capturing a new baseline. The baseline is read-only and does not authorize writes.");
        addEntry(faq,"Why was baseline capture refused?",
            "1. Open Create Bootable USB and select the intended USB as the target. You do not need to choose an ISO or start a write.\n"
            "2. Return to Device Safety, choose Capture new advisory baseline, and confirm. Look for MATCHED.\n"
            "3. If capture is refused again, refresh the device list and confirm that the drive is still connected. The app also requires a reported serial number or WWN to capture a baseline.\n"
            "The dropdown under Integrated Storage Inspection is for the read-only inspection. Baseline capture uses the target selected on Create Bootable USB.");
        addEntry(faq,"Can I compare a Windows installer USB with the ISO?",
            "Windows mode creates a FAT32 installer from the files inside the ISO. The app verifies the prepared image during writing. Use Calculate / Verify SHA-256 to check the original ISO against its publisher’s checksum, and the computer’s UEFI boot menu to test the USB.");
        addEntry(faq,"Did the simulation write my ISO?","The simulation checks your selection without writing. Use the Linux or Windows write button for your image type.");
        addEntry(faq,"Can USB Repair fix NTFS or physical damage?","NTFS has a limited read-only check. Automatic repair supports FAT, exFAT and ext4. Back up readable files first. Physical damage requires other recovery options.");
        faq->addStretch();
        layout->addWidget(help,1);
        return page;
    }
    QWidget* otherPage(int index){
        if(index==8)return aboutPage();
        auto *w=new QWidget;w->setObjectName("content");auto *v=column(w,9,16);
        v->addWidget(txt(names[index],24,true,"white"));
        QStringList subs={"","Choose an ISO image and a removable USB drive.","Copy a USB drive to another device.","Format a removable USB drive.","Verify ISO image integrity.","Inspect USB drives and identify potential problems.","Inspect device identity and topology.","Application preferences.","About Jatayu USB Studio.","Download Linux ISO images over HTTPS."};
        v->addWidget(txt(subs[index],12,false,"#dbe7ff"));
        auto *p=frame(index==1?"workflow":"light");auto *pv=column(p,index==1?6:8,index==1?13:16);
        if(index==1){
            pv->addWidget(txt("USB Image Setup",19,true,"#F5F9FF"));
            pv->addWidget(txt("STEP 1  ·  ISO IMAGE",12,true,"#DCEBFF"));
            auto *isoRow=new QHBoxLayout;iso=new QLineEdit;iso->setReadOnly(true);iso->setPlaceholderText("Choose a local ISO image…");
            auto *browse=new QPushButton("Browse…");browse->setObjectName("secondary");isoRow->addWidget(iso,1);isoRow->addWidget(browse);pv->addLayout(isoRow);
            connect(browse,&QPushButton::clicked,this,[this]{
                // Use the platform's native file chooser. On KDE Plasma with the
                // KDE Qt platform integration installed, this provides the same
                // KIO Places/Devices integration as other KDE applications.
                // Unlike QStorageInfo, KIO can list unmounted partitions and
                // prompt for mounting when the user explicitly selects one.
                // No mounts are performed by Jatayu USB Studio itself.
                // IMPORTANT: nullptr parent prevents the main window's custom
                // Qt stylesheet from cascading into KDE's native dialog.
                // The native chooser remains application-modal.
                const QString f = QFileDialog::getOpenFileName(
                    nullptr, "Select ISO Image", QDir::homePath(),
                    "ISO Images (*.iso);;All Files (*)");
                if (f.isEmpty()) return;
                QFileInfo fi(f);iso->setText(f);
                if(!fi.isFile() || !fi.isReadable() || fi.size()<=0 || fi.suffix().compare("iso",Qt::CaseInsensitive)!=0)
                    isoStatus->setText("Invalid ISO selection: choose a readable, nonempty .iso file.");
                else isoStatus->setText("Selected: "+fi.fileName()+" · "+sizeText(quint64(fi.size()))+" · File accessible (image integrity not verified)");
            });
            isoStatus=txt("No ISO selected. Image integrity has not been verified.",10,false,"#C4D5F0");pv->addWidget(isoStatus);
            pv->addWidget(txt("STEP 2  ·  USB TARGET",12,true,"#DCEBFF"));target=new QComboBox;target->setView(new QListView(target));target->setMaxVisibleItems(8);target->addItem("Scanning USB drives…");pv->addWidget(target);
            pv->addWidget(txt("STEP 3  ·  SAFETY & VERIFICATION",12,true,"#DCEBFF"));
            auto *modeInfo=txt("Raw ISO image writing with SHA-256 readback",11,false,"#C4D5F0");
            modeInfo->setObjectName("modeInfo");pv->addWidget(modeInfo);
            // Beta 60: GUI-integrated, unprivileged ISO hash verification.
            // Deliberately never invokes the experimental raw-device writer.
            auto *isoVerify=new QPushButton("Verify ISO SHA-256 (read-only)");
            isoVerify->setObjectName("secondary");pv->addWidget(isoVerify);
            auto *isoVerifyResult=txt("ISO SHA-256 not calculated in this session.",10,false,"#C4D5F0");
            isoVerifyResult->setWordWrap(true);isoVerifyResult->setTextInteractionFlags(Qt::TextSelectableByMouse);
            pv->addWidget(isoVerifyResult);
            connect(isoVerify,&QPushButton::clicked,this,[this,isoVerify,isoVerifyResult]{
                if(!iso || !QFileInfo(iso->text()).isFile()){
                    QMessageBox::warning(this,"Choose an ISO","Select a regular ISO file first.");return;
                }
                const QString script=backendFile("iso_write_preflight.py");
                if(!QFileInfo::exists(script)){
                    isoVerifyResult->setText("ISO verification backend missing. No operation performed.");return;
                }
                auto *process=new QProcess(this);
                auto *timeout=new QTimer(process);timeout->setSingleShot(true);
                const QString selected=iso->text();
                isoVerify->setEnabled(false);isoVerifyResult->setText("Calculating SHA-256 (read-only)…");
                connect(timeout,&QTimer::timeout,process,[process]{process->kill();});
                connect(process,QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),this,
                    [process,timeout,isoVerify,isoVerifyResult,selected](int code,QProcess::ExitStatus status){
                        timeout->stop();isoVerify->setEnabled(true);
                        QJsonParseError parse;
                        auto doc=QJsonDocument::fromJson(process->readAllStandardOutput(),&parse);
                        const auto obj=doc.object();
                        if(status==QProcess::NormalExit && code==0 && parse.error==QJsonParseError::NoError
                           && obj.value("ok").toBool(false) && !obj.value("writing_enabled").toBool(true)
                           && obj.value("sha256").toString().size()==64){
                            isoVerifyResult->setText("ISO checksum calculated: "+QFileInfo(selected).fileName()
                                +"\nSHA-256: "+obj.value("sha256").toString());
                        }else isoVerifyResult->setText("ISO verification failed or timed out. No USB writes performed.");
                        process->deleteLater();
                    });
                connect(process,&QProcess::errorOccurred,this,[process,timeout,isoVerify,isoVerifyResult](QProcess::ProcessError){
                    if(process->state()!=QProcess::NotRunning)return;
                    timeout->stop();isoVerify->setEnabled(true);
                    isoVerifyResult->setText("ISO verification could not start. No USB writes performed.");
                });
                process->start("/usr/bin/python3",{"-B","-E","-s",script,"--iso",selected});
                timeout->start(120000);
            });
            auto *write=new QPushButton("Write hybrid Linux ISO");
            write->setObjectName("primary");pv->addWidget(write);
            const auto startWrite=[this](const QString &mode){
                const QFileInfo image(iso->text());
                const auto selection=selectionArguments(target);
                if(selection.isEmpty() || !image.isFile() || !image.isReadable() || image.size()<=0 ||
                   image.suffix().compare("iso",Qt::CaseInsensitive)!=0){
                    QMessageBox::warning(this,"USB write","Select a readable ISO and a removable USB drive.");return;
                }
                const auto found=std::find_if(devices.cbegin(),devices.cend(),[&](const Drive &d){return d.path==selection[1];});
                if(found==devices.cend() || quint64(image.size())>found->bytes){
                    QMessageBox::warning(this,"USB write","The ISO exceeds the selected drive capacity or the drive was disconnected.");return;
                }
                const QString path=selection[1];
                const QString shown=target->currentText();
                if(confirmErase(path,"All data on "+shown+" will be overwritten by "+image.fileName()+". Unmount all its partitions first."))
                    runOperation(mode=="windows"?"Create Windows installer":"Create Bootable USB",QStringList{mode,"--iso",image.absoluteFilePath(),"--confirm","ERASE "+path}+selection,
                                 {"WRITTEN_AND_VERIFIED"});
            };
            connect(write,&QPushButton::clicked,this,[startWrite]{startWrite("write");});
            pv->addWidget(txt("Copies a hybrid Linux ISO byte for byte and checks SHA-256 readback.",11));
            auto *windows=new QPushButton("Create Windows installer (UEFI)");
            windows->setObjectName("primary");pv->addWidget(windows);
            connect(windows,&QPushButton::clicked,this,[startWrite]{startWrite("windows");});
            pv->addWidget(txt("Prepares FAT32 media from a Windows x64 ISO. Requires a UEFI computer and free local workspace.",11));
            auto *create=new QPushButton("Inspect USB Write Safety");create->setObjectName("secondary");pv->addWidget(create);
            connect(create,&QPushButton::clicked,this,[this]{
                const auto selection=selectionArguments(target);
                if(selection.isEmpty()){
                    QMessageBox::warning(this,"Inspect USB","Select a USB drive with a known disk generation.");return;
                }
                runOperation("Inspect USB Write Safety",QStringList{"inspect"}+selection,{"SAFETY_CHECKED"});
            });
            pv->addWidget(txt("Creating a bootable USB overwrites the selected drive. Unmount the drive before starting.",11,true,"#8B261E"));
        } else if(index==7){
            pv->addWidget(txt("USB device discovery",19,true));
            auto *check=new QCheckBox("Automatically refresh USB devices every 2.5 seconds");
            check->setStyleSheet("color:#142644;");
            check->setChecked(preferences.value("devices/autoRefresh",true).toBool());
            pv->addWidget(check);
            connect(check,&QCheckBox::toggled,this,[this](bool enabled){
                preferences.setValue("devices/autoRefresh",enabled);
                if(enabled){refreshTimer.start(2500);refreshDrives();}
                else refreshTimer.stop();
            });
            auto *refresh=new QPushButton("Refresh USB devices now");
            refresh->setObjectName("secondary");pv->addWidget(refresh,0,Qt::AlignLeft);
            connect(refresh,&QPushButton::clicked,this,&Studio::refreshDrives);
            pv->addWidget(txt("Destructive operations require an unmounted removable USB drive and explicit confirmation.",11));
            auto *advanced=frame("light");auto *advancedLayout=column(advanced,8,12);
            advancedLayout->addWidget(txt("Run a USB simulation or test an ISO copy to a new file.",11));
            auto *isoRow=new QHBoxLayout;
            auto *diagnosticIso=new QLineEdit;
            diagnosticIso->setReadOnly(true);
            diagnosticIso->setPlaceholderText("Choose a local ISO image…");
            diagnosticIso->setAccessibleName("Developer Tools ISO image");
            auto *browse=new QPushButton("Browse…");
            browse->setObjectName("secondary");
            isoRow->addWidget(diagnosticIso,1);isoRow->addWidget(browse);
            advancedLayout->addLayout(isoRow);
            connect(browse,&QPushButton::clicked,this,[diagnosticIso]{
                const auto file=QFileDialog::getOpenFileName(nullptr,"Select ISO Image",QDir::homePath(),"ISO Images (*.iso);;All Files (*)");
                if(!file.isEmpty())diagnosticIso->setText(file);
            });
            auto *diagnosticTarget=operationPicker(advancedLayout);
            diagnosticTarget->setAccessibleName("Developer Tools simulation USB target");
            auto *simulate=new QPushButton("Simulate USB Writing — No Disk Changes");
            simulate->setObjectName("secondary");advancedLayout->addWidget(simulate);
            auto *writeProgress=new QProgressBar;writeProgress->setRange(0,100);writeProgress->setValue(0);writeProgress->setFixedHeight(16);advancedLayout->addWidget(writeProgress);
            auto *writeStatus=txt("Simulation idle. No USB writes.",11);advancedLayout->addWidget(writeStatus);
            // Beta 25: safe regular-file copy preview. Never passes a USB path.
            auto *demoPanel=frame("light");auto *demoLayout=column(demoPanel,8,12);
            demoLayout->addWidget(txt("File-backed progress laboratory",14,true));
            demoLayout->addWidget(txt("Copy a selected ISO into a NEW regular file, then verify SHA-256. No USB device access. Do not use as root.",10));
            auto *demoPhase=txt("Idle — no file operation started",11);demoLayout->addWidget(demoPhase);
            auto *copyLabel=txt("Copying · 0%",10,true);demoLayout->addWidget(copyLabel);
            auto *demoProgress=new QProgressBar;demoProgress->setRange(0,100);demoProgress->setValue(0);demoLayout->addWidget(demoProgress);
            auto *verifyLabel=txt("Verifying SHA-256 · 0%",10,true);demoLayout->addWidget(verifyLabel);
            auto *verifyProgress=new QProgressBar;verifyProgress->setRange(0,100);verifyProgress->setValue(0);demoLayout->addWidget(verifyProgress);
            auto *demoMetrics=txt("0% · 0 B/s · 0s",10);demoLayout->addWidget(demoMetrics);
            auto *demoButtons=new QHBoxLayout;
            auto *demoStart=new QPushButton("Copy ISO to new file (test)");demoStart->setObjectName("primary");
            auto *demoCancel=new QPushButton("Cancel file copy");demoCancel->setObjectName("secondary");demoCancel->setEnabled(false);
            demoButtons->addWidget(demoStart);demoButtons->addWidget(demoCancel);demoLayout->addLayout(demoButtons);
            advancedLayout->addWidget(demoPanel);
            connect(demoStart,&QPushButton::clicked,this,[this,diagnosticIso,demoStart,demoCancel,demoPhase,demoProgress,verifyProgress,copyLabel,verifyLabel,demoMetrics]{
                if(fileDemo) return;
                QFileInfo source(diagnosticIso->text());
                if(!source.isFile() || !source.isReadable() || source.size()<=0 || source.suffix().compare("iso",Qt::CaseInsensitive)!=0){
                    QMessageBox::warning(this,"ISO required","Select a readable, nonempty ISO file first.");return;
                }
                const QString dest=QFileDialog::getSaveFileName(this,"Choose NEW output file (never a USB device)",QDir::homePath()+"/iso-copy-test.img","Image files (*.img);;All files (*)");
                if(dest.isEmpty()) return;
                if(QFileInfo::exists(dest) || QFileInfo(dest).isSymLink()){
                    QMessageBox::warning(this,"Existing destination","Choose a new filename. Existing files are never overwritten.");return;
                }
                const QString bridge=backendFile("file_copy_demo_cli.py");
                if(!QFileInfo(bridge).isFile()){QMessageBox::critical(this,"Missing bridge","File copy bridge is unavailable.");return;}
                cancelDirectory=new QTemporaryDir;
                if(!cancelDirectory->isValid()){delete cancelDirectory;cancelDirectory=nullptr;return;}
                const QString cancelPath=cancelDirectory->path()+"/cancel";
                fileDemo=new QProcess(this);demoBuffer.clear();demoProgress->setValue(0);verifyProgress->setValue(0);
                copyLabel->setText("Copying · 0%");verifyLabel->setText("Verifying SHA-256 · 0%");
                fileDemo->setProperty("resultReceived",false);
                demoStart->setEnabled(false);demoCancel->setEnabled(true);demoPhase->setText("Preparing safe file copy…");
                connect(demoCancel,&QPushButton::clicked,fileDemo,[cancelPath,demoCancel]{
                    QFile marker(cancelPath);if(marker.open(QIODevice::WriteOnly))marker.close();demoCancel->setEnabled(false);
                });
                connect(fileDemo,&QProcess::readyReadStandardOutput,this,[this,demoPhase,demoProgress,verifyProgress,copyLabel,verifyLabel,demoMetrics]{
                    demoBuffer+=fileDemo->readAllStandardOutput();
                    while(true){const int pos=demoBuffer.indexOf('\n');if(pos<0)break;
                        const QByteArray line=demoBuffer.left(pos);demoBuffer.remove(0,pos+1);
                        const auto doc=QJsonDocument::fromJson(line);if(!doc.isObject())continue;
                        const auto obj=doc.object();
                        if(obj.value("type").toString()=="progress"){
                            const double done=obj.value("bytes_done").toDouble(),total=obj.value("bytes_total").toDouble();
                            const int pct=total>0?int(std::clamp(done/total*100.0,0.0,100.0)):0;
                            const QString phase=obj.value("phase").toString();
                            if(phase=="copy") {demoProgress->setValue(pct);copyLabel->setText(QString("Copying · %1%").arg(pct));}
                            else if(phase=="verify") {verifyProgress->setValue(pct);verifyLabel->setText(QString("Verifying SHA-256 · %1%").arg(pct));}
                            demoPhase->setText(phase=="verify"?"Verifying copied file…":"Copying to new regular file…");
                            demoMetrics->setText(QString("%1% · %2/s · %3s").arg(pct).arg(sizeText(quint64(std::max(0.0,obj.value("bytes_per_second").toDouble())))).arg(obj.value("elapsed_seconds").toDouble(),0,'f',1));
                        } else if(obj.value("type").toString()=="result"){
                            fileDemo->setProperty("resultReceived",true);
                            if(obj.value("ok").toBool()) {
                                demoProgress->setValue(100);verifyProgress->setValue(100);
                                copyLabel->setText("Copying · 100%");verifyLabel->setText("Verifying SHA-256 · 100%");
                                demoPhase->setText("Success — SHA-256 verified (regular file only)");
                            } else if(obj.value("cancelled").toBool()) demoPhase->setText("Cancelled — file copy stopped; incomplete output cleanup requested");
                            else demoPhase->setText("Failed — "+obj.value("error").toString());
                        }
                    }
                });
                connect(fileDemo,QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),this,[this,demoStart,demoCancel,demoPhase](int code,QProcess::ExitStatus exit){
                    if(!fileDemo->property("resultReceived").toBool()) {
                        demoPhase->setText("Interrupted — no final result received; check output file before retrying");
                    } else if(code!=0 && demoPhase->text().startsWith("Success")) {
                        demoPhase->setText("Failed — process exited unsuccessfully; verify output manually");
                    }
                    fileDemo->deleteLater();fileDemo=nullptr;
                    delete cancelDirectory;cancelDirectory=nullptr;
                    demoStart->setEnabled(true);demoCancel->setEnabled(false);
                });
                connect(fileDemo,&QProcess::errorOccurred,this,[this,demoPhase](QProcess::ProcessError){
                    demoPhase->setText("Unable to launch file-copy bridge; no copy started.");
                });
                fileDemo->start("/usr/bin/python3",{"-B","-E","-s",bridge,"--source",source.absoluteFilePath(),"--destination",dest,"--cancel-file",cancelPath});
            });
            connect(simulate,&QPushButton::clicked,this,[this,diagnosticIso,diagnosticTarget,writeProgress,writeStatus]{
                QFileInfo image(diagnosticIso->text());
                if(!image.isFile() || !image.isReadable() || image.size()<=0 || image.suffix().compare("iso",Qt::CaseInsensitive)!=0){
                    QMessageBox::warning(this,"Invalid ISO","Choose a readable, nonempty ISO file.");return;
                }
                QString dev=diagnosticTarget->currentData().toString();
                auto found=std::find_if(devices.cbegin(),devices.cend(),[&](const Drive &d){return d.path==dev;});
                if(found==devices.cend() || quint64(image.size())>found->bytes){
                    QMessageBox::warning(this,"Invalid target","Select a detected USB drive large enough for the image.");return;
                }
                const QString backend=backendFile("simulation_backend.py");
                if(!QFileInfo(backend).isFile()){
                    QMessageBox::critical(this,"Simulation unavailable","Simulation backend missing. No disk was modified.");return;
                }
                auto confirm=QMessageBox::question(this,"Simulation only — no writing",
                    "Selected target: "+dev+"\nModel: "+found->name+"\nCapacity: "+QString::number(found->bytes / (1024.0*1024*1024),'f',1)+" GiB\nISO: "+image.fileName()+"\n\nSIMULATION ONLY. No data will be erased or written.\n\nContinue?",
                    QMessageBox::Yes|QMessageBox::No,QMessageBox::No);
                if(confirm!=QMessageBox::Yes) return;
                writeProgress->setValue(5);writeStatus->setText("Running read-only simulation checks…");
                QProcess proc;
                proc.start("/usr/bin/python3",{"-B","-E","-s",backend,"--target",dev,"--iso",image.absoluteFilePath()});
                QString error;QJsonObject result;
                if(!proc.waitForStarted(3000)) error="Simulation backend failed to start";
                else if(!proc.waitForFinished(20000)){
                    proc.kill();proc.waitForFinished(1000);error="Simulation timed out";
                } else if(proc.exitStatus()!=QProcess::NormalExit || proc.exitCode()!=0)
                    error="Simulation backend error: "+QString::fromUtf8(proc.readAllStandardError()).left(250);
                else {
                    QJsonParseError parse;
                    auto doc=QJsonDocument::fromJson(proc.readAllStandardOutput(),&parse);
                    if(parse.error!=QJsonParseError::NoError || !doc.isObject()) error="Invalid simulation response";
                    else result=doc.object();
                }
                bool ok=error.isEmpty() && result.value("simulation_complete").toBool(false)
                    && result.value("read_only").toBool(false)
                    && !result.value("allowed_to_write").toBool(true)
                    && result.value("target").toString()==dev;
                writeProgress->setValue(ok?100:0);
                writeStatus->setText(ok?"Read-only simulation complete — zero disk writes.":"Simulation blocked or unavailable — zero disk writes.");
                QString detail=error.isEmpty()?result.value("message").toString():error;
                const auto reasons=result.value("reasons").toArray();
                for(const auto &r:reasons) detail+="\n• "+r.toString();
                QMessageBox box(this);box.setWindowTitle("USB Write Simulation — Read Only");
                box.setIcon(ok?QMessageBox::Information:QMessageBox::Warning);
                box.setText(ok?"SIMULATION COMPLETE — NO DATA WRITTEN":"SIMULATION BLOCKED — NO DATA WRITTEN");
                box.setInformativeText(detail+"\n\nThis simulation performs no disk writes.");box.exec();
            });
            auto *advancedToggle=new QPushButton("Developer Tools");
            advancedToggle->setObjectName("secondary");
            advancedToggle->setCheckable(true);
            advanced->setVisible(false);
            connect(advancedToggle,&QPushButton::toggled,advanced,&QWidget::setVisible);
            pv->addWidget(advancedToggle,0,Qt::AlignLeft);
            pv->addWidget(advanced);
        } else if(index==4){
            pv->addWidget(txt("Verify ISO SHA-256 checksum",19,true));
            pv->addWidget(txt("Calculate the SHA-256 digest of a local ISO file and optionally compare it with a trusted published checksum. No USB device is modified.",12));
            auto *pathRow=new QHBoxLayout;
            auto *pathField=new QLineEdit;pathField->setReadOnly(true);pathField->setPlaceholderText("Select an ISO file…");
            auto *pick=new QPushButton("Browse…");pick->setObjectName("secondary");
            pathRow->addWidget(pathField,1);pathRow->addWidget(pick);pv->addLayout(pathRow);
            auto *expected=new QLineEdit;expected->setPlaceholderText("Optional trusted SHA-256 (64 hexadecimal characters)");pv->addWidget(expected);
            auto *checksumRow=new QHBoxLayout;
            auto *checksumFile=new QLineEdit;checksumFile->setReadOnly(true);checksumFile->setPlaceholderText("Optional publisher checksum file (SHA256SUMS / .sha256)");
            auto *chooseChecksum=new QPushButton("Checksum file…");chooseChecksum->setObjectName("secondary");
            checksumRow->addWidget(checksumFile,1);checksumRow->addWidget(chooseChecksum);pv->addLayout(checksumRow);
            pv->addWidget(txt("A checksum match proves integrity against the supplied reference, not publisher authenticity. Verify the reference or its digital signature separately.",10));
            connect(chooseChecksum,&QPushButton::clicked,this,[this,checksumFile](){
                const QString chosen=QFileDialog::getOpenFileName(this,"Select publisher SHA-256 checksum file",QDir::homePath(),"Checksum files (*.sha256 *.sha256sum *.txt SHA256SUMS SHA256SUMS.txt);;All files (*)");
                if(!chosen.isEmpty())checksumFile->setText(chosen);
            });
            auto *hashButton=new QPushButton("Calculate / Verify SHA-256");pv->addWidget(hashButton);
            auto *result=txt("No checksum calculated.",11);result->setTextInteractionFlags(Qt::TextSelectableByMouse);result->setWordWrap(true);pv->addWidget(result);
            connect(pick,&QPushButton::clicked,this,[this,pathField](){
                QString selected=QFileDialog::getOpenFileName(this,"Select ISO Image",QDir::homePath(),"ISO Images (*.iso);;All Files (*)");
                if(!selected.isEmpty())pathField->setText(selected);
            });
            connect(hashButton,&QPushButton::clicked,this,[this,pathField,expected,checksumFile,result,hashButton](){
                QString file=pathField->text();QFileInfo info(file);
                if(!info.isFile() || !info.isReadable() || info.size()<=0){QMessageBox::warning(this,"Invalid ISO","Select a readable, nonempty ISO file.");return;}
                QString reference=expected->text().trimmed().toLower();
                if(!reference.isEmpty() && !QRegularExpression("^[0-9a-f]{64}$").match(reference).hasMatch()){
                    QMessageBox::warning(this,"Invalid checksum","Expected SHA-256 must contain exactly 64 hexadecimal characters.");return;
                }
                if(!checksumFile->text().isEmpty()){
                    if(!reference.isEmpty()){
                        QMessageBox::warning(this,"Choose one reference","Use either a pasted SHA-256 or a checksum file, not both.");return;
                    }
                    QFile checksums(checksumFile->text());
                    if(!checksums.open(QIODevice::ReadOnly) || checksums.size()>1024*1024){
                        QMessageBox::warning(this,"Checksum file","Cannot read checksum file or file is too large (maximum 1 MiB).");return;
                    }
                    const QString contents=QString::fromUtf8(checksums.readAll());
                    const QString targetName=info.fileName();
                    QStringList matches;
                    const QRegularExpression sumLine(R"(^\s*([0-9a-fA-F]{64})\s+\*?(.+?)\s*$)");
                    const QRegularExpression bareLine(R"(^\s*([0-9a-fA-F]{64})\s*$)");
                    for(const QString &line:contents.split('\n')){
                        const auto m=sumLine.match(line);
                        if(m.hasMatch() && m.captured(2)==targetName) matches<<m.captured(1).toLower();
                        else if(bareLine.match(line).hasMatch()) matches<<bareLine.match(line).captured(1).toLower();
                    }
                    if(matches.size()!=1){
                        QMessageBox::warning(this,"Checksum file","Expected exactly one SHA-256 entry matching this ISO filename (or one bare hash). Found "+QString::number(matches.size())+". No verification performed.");return;
                    }
                    reference=matches.first();
                }
                hashButton->setEnabled(false);result->setText("Calculating SHA-256… Please wait.");
                auto *proc=new QProcess(this);
                connect(proc,QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),this,[proc,result,hashButton,reference,file](int code,QProcess::ExitStatus status){
                    hashButton->setEnabled(true);
                    QString output=QString::fromUtf8(proc->readAllStandardOutput());
                    QString digest=output.left(64).toLower();
                    if(status!=QProcess::NormalExit || code!=0 || !QRegularExpression("^[0-9a-f]{64}$").match(digest).hasMatch())
                        result->setText("SHA-256 calculation failed. File may have changed or become unavailable.");
                    else if(reference.isEmpty())result->setText("SHA-256: "+digest+"\nCompare this with the publisher's trusted checksum.");
                    else result->setText("SHA-256: "+digest+(digest==reference?"\nMATCH — ISO matches the supplied reference checksum (publisher authenticity not established).":"\nMISMATCH — do not use this ISO."));
                    proc->deleteLater();
                });
                connect(proc,&QProcess::errorOccurred,this,[proc,result,hashButton](QProcess::ProcessError){
                    hashButton->setEnabled(true);result->setText("Unable to start SHA-256 calculation.");proc->deleteLater();
                });
                proc->start("/usr/bin/sha256sum",QStringList{"--zero","--",file});
            });
            pv->addWidget(txt("Compare a raw-written USB against the selected ISO. Windows installer mode prepares a different image and verifies it during writing.",11));
            auto *usb=operationPicker(pv);
            auto *verify=new QPushButton("Verify written USB against ISO");
            pv->addWidget(verify);
            connect(verify,&QPushButton::clicked,this,[this,pathField,usb]{
                const auto selection=selectionArguments(usb);
                if(selection.isEmpty() || !QFileInfo(pathField->text()).isFile()){
                    QMessageBox::warning(this,"Verify USB","Choose an ISO and an unmounted USB drive.");return;
                }
                runOperation("Verify USB",QStringList{"verify","--iso",pathField->text()}+selection,{"IMAGE_MATCH"});
            });
        } else if(index==2 || index==3){
            const bool clone=index==2;
            pv->addWidget(txt(clone?"Clone USB":"Format USB",19,true));
            pv->addWidget(txt(clone?"Copy and verify the full source disk. Both drives must be unmounted."
                :"Create a filesystem across the selected device. This erases the old partition table and all data.",11));
            QComboBox *source=nullptr;
            if(clone){pv->addWidget(txt("Source drive",11,true));source=operationPicker(pv);}
            pv->addWidget(txt("Destination drive",11,true));
            auto *destination=operationPicker(pv);
            auto *fs=new QComboBox(p);
            auto *fullFormat=new QCheckBox("Full format (overwrite and verify the entire drive)",p);
            fullFormat->setStyleSheet("color:#142644;");
            if(!clone){
                fs->addItem("FAT32","vfat");fs->addItem("exFAT","exfat");fs->addItem("NTFS","ntfs");fs->addItem("ext4","ext4");
                pv->addWidget(fs);
                pv->addWidget(fullFormat);
                connect(fs,&QComboBox::currentIndexChanged,this,[fs,fullFormat]{fullFormat->setVisible(fs->currentData()=="vfat");});
                pv->addWidget(txt("FAT32 quick format replaces filesystem metadata. Old data may remain recoverable. Other filesystems use full format.",10));
                pv->addWidget(txt("FAT32 works with many older devices and limits individual files to 4 GiB. exFAT supports large files across modern systems. NTFS is commonly used with Windows. ext4 is designed for Linux.",10));
            }else {fs->hide();fullFormat->hide();}
            auto *refresh=new QPushButton("Refresh USB drives");pv->addWidget(refresh);
            connect(refresh,&QPushButton::clicked,this,&Studio::refreshDrives);
            auto *start=new QPushButton(clone?"Clone USB":"Format USB");pv->addWidget(start);
            if(clone){
                cloneSource=source;
                cloneDestination=destination;
                cloneStart=start;
                start->setEnabled(false);
                pv->addWidget(txt("Cloning requires two separate USB drives. The destination must be at least as large as the source.",10));
                connect(source,&QComboBox::currentIndexChanged,this,&Studio::populateCloneDestination);
                connect(destination,&QComboBox::currentIndexChanged,this,&Studio::updateCloneAction);
            }
            connect(start,&QPushButton::clicked,this,[this,clone,source,destination,fs,fullFormat]{
                auto targetArgs=selectionArguments(destination);
                const auto sourceArgs=clone?selectionArguments(source,true):QStringList();
                if(targetArgs.isEmpty() || (clone && (sourceArgs.isEmpty() || sourceArgs[1]==targetArgs[1] ||
                       destination->currentData(Qt::UserRole+1).toULongLong()<source->currentData(Qt::UserRole+1).toULongLong()))){
                    QMessageBox::warning(this,"Check selection",clone?"Choose two distinct drives and a destination at least as large as the source.":"Choose the removable drive to format.");return;
                }
                const QString description=clone?"Clone "+source->currentText()+" onto "+destination->currentText()
                    :"Format "+destination->currentText()+" as "+fs->currentText();
                if(!confirmErase(targetArgs[1],description+". All data on the destination will be lost."))return;
                auto options=clone?sourceArgs:QStringList{"--filesystem",fs->currentData().toString()};
                if(!clone && fullFormat->isChecked())options<<"--full-format";
                runOperation(clone?"Clone USB":"Format USB",QStringList{clone?"clone":"format","--confirm","ERASE "+targetArgs[1]}+targetArgs+options,
                             clone?QStringList{"WRITTEN_AND_VERIFIED"}:QStringList{"WRITTEN_AND_VERIFIED","QUICK_FORMAT_VERIFIED"});
            });
        } else if(index==5){
            pv->addWidget(txt("USB Repair & Recovery",19,true));
            pv->addWidget(txt("Check a FAT, exFAT, NTFS or ext4 filesystem without modifying the USB. Automatic repair supports FAT, exFAT and ext4. Unmount all filesystems on the drive. Health checks run directly when UDisks2 supports them. Repair and fallback checks need temporary space equal to the selected filesystem. Software cannot repair physical damage.",11));
            pv->addWidget(txt("Select a partition or filesystem. One USB drive can contain several partitions.",11,true));
            auto *usb=operationPicker(pv,true);
            auto *refresh=new QPushButton("Refresh USB filesystems");pv->addWidget(refresh);
            connect(refresh,&QPushButton::clicked,this,&Studio::refreshDrives);
            auto *check=new QPushButton("Check filesystem health");pv->addWidget(check);
            auto *repair=new QPushButton("Repair filesystem");pv->addWidget(repair);
            auto start=[this,usb](bool modify){
                const auto selection=selectionArguments(usb);
                if(selection.isEmpty()){QMessageBox::warning(this,"USB filesystem","Select an unmounted USB filesystem.");return;}
                const QString partition=usb->currentData(Qt::UserRole+3).toString();
                if(modify && usb->currentData(Qt::UserRole+4).toString().compare("ntfs",Qt::CaseInsensitive)==0){
                    QMessageBox::information(this,"NTFS repair","Automatic NTFS repair is unavailable. Use Windows chkdsk to repair NTFS.");
                    return;
                }
                if(modify && !confirmErase(selection[1],"Repair "+partition+" on "+usb->currentText()+
                        ". Back up the drive first. An interrupted repair write may damage the filesystem."))return;
                runOperation(modify?"Repair filesystem":"Check filesystem",
                    QStringList{modify?"repair":"check","--partition",partition,"--confirm",modify?"ERASE "+selection[1]:QString("read-only")}+selection,
                    modify?QStringList{"FILESYSTEM_CLEAN","WRITTEN_AND_VERIFIED"}:QStringList{"FILESYSTEM_CLEAN","FILESYSTEM_FINDINGS"});
            };
            connect(check,&QPushButton::clicked,this,[start]{start(false);});
            connect(repair,&QPushButton::clicked,this,[start]{start(true);});
        } else if(index==9){
            pv->addWidget(txt("Download a Linux ISO over HTTPS. Compare its SHA-256 with the checksum published by your distribution before writing it.",11));
            auto *url=new QLineEdit;url->setPlaceholderText("https://…/distribution.iso");pv->addWidget(url);
            auto *folder=new QLineEdit;folder->setReadOnly(true);folder->setPlaceholderText("Choose a destination folder");
            auto *row=new QHBoxLayout;row->addWidget(folder,1);
            auto *browse=new QPushButton("Choose folder…");row->addWidget(browse);pv->addLayout(row);
            connect(browse,&QPushButton::clicked,this,[this,folder]{
                const QString path=QFileDialog::getExistingDirectory(this,"Choose download folder",QDir::homePath());
                if(!path.isEmpty())folder->setText(path);
            });
            auto *download=new QPushButton("Download ISO");pv->addWidget(download);
            auto *use=new QPushButton("Use downloaded ISO");use->setEnabled(false);pv->addWidget(use);
            connect(download,&QPushButton::clicked,this,[this,url,folder,use]{
                if(url->text().trimmed().isEmpty() || folder->text().isEmpty()){
                    QMessageBox::warning(this,"Download ISO","Enter an HTTPS ISO URL and choose a destination folder.");return;
                }
                runOperation("Download ISO",{"download","--url",url->text().trimmed(),"--directory",folder->text()},
                    {"DOWNLOADED"},[use](const QJsonObject &result){
                        use->setProperty("isoPath",result.value("path").toString());use->setEnabled(true);
                    });
            });
            connect(use,&QPushButton::clicked,this,[this,use]{
                const QString downloaded=use->property("isoPath").toString();
                if(!QFileInfo(downloaded).isFile()){
                    QMessageBox::warning(this,"Download unavailable","The downloaded ISO was moved or removed.");return;
                }
                iso->setText(downloaded);isoStatus->setText("Selected download: "+QFileInfo(downloaded).fileName());selectPage(1);
            });
        }
        if(index==1){
            // Existing labels use explicit dark-on-light colors. Recolor only
            // labels inside this workflow, not dialogs or the home dashboard.
            for(auto *label:p->findChildren<QLabel*>()){
                QString style=label->styleSheet();
                style.replace("#142644","#EAF2FF",Qt::CaseInsensitive);
                style.replace("#334766","#BFD5F6",Qt::CaseInsensitive);
                style.replace("#C4D5F0","#BFD5F6",Qt::CaseInsensitive);
                style.replace("#8B261E","#FFB9A9",Qt::CaseInsensitive);
                label->setStyleSheet(style);
            }
        }
        v->addWidget(p);v->addStretch();return wrapPage(w);
    }
    bool eventFilter(QObject *obj,QEvent *event) override {
        if(event->type()==QEvent::MouseButtonRelease && obj->property("destination").isValid()){
            selectPage(obj->property("destination").toInt());return true;
        }
        return QMainWindow::eventFilter(obj,event);
    }
    void refreshDrives(){
        if(scan) return; // Never overlap asynchronous scans.
        QHash<QString,QString> sequences;
        for(const QString &name:QDir("/sys/block").entryList(QDir::Dirs|QDir::NoDotAndDotDot)){
            const QString generation=readDiskSequence(name);
            if(!generation.isEmpty())sequences.insert(name,generation);
        }
        scan=new QProcess(this);auto *p=scan;
        p->setProgram("lsblk");p->setArguments(usbLsblkArguments());
        // A stalled lsblk must never leave an old MATCHED state on screen.
        auto timedOut=std::make_shared<bool>(false);
        QTimer::singleShot(6000,this,[this,p,timedOut]{
            if(scan!=p || p->state()==QProcess::NotRunning)return;
            *timedOut=true;
            p->kill(); // finished callback handles fail-closed invalidation.
        });
        connect(p,QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),this,[this,p,timedOut,sequences](int code,QProcess::ExitStatus exit){
            if(scan!=p)return;
            QString previous=target?target->currentData().toString():selectedPath;
            QVector<Drive> found;
            bool validSnapshot=false;
            if(!*timedOut && code==0 && exit==QProcess::NormalExit){
                QJsonParseError err;auto doc=QJsonDocument::fromJson(p->readAllStandardOutput(),&err);
                validSnapshot=(err.error==QJsonParseError::NoError && doc.isObject() &&
                    doc.object().value("blockdevices").isArray());
                if(validSnapshot){
                    for(const auto &val:doc.object().value("blockdevices").toArray()){
                        auto d=val.toObject();
                        if(!usbDisk(d))continue;
                        Drive dev;dev.path=d.value("path").toString();dev.name=d.value("model").toString().trimmed();dev.identity=guiFingerprint(d);
                        const QString name=QFileInfo(dev.path).fileName();
                        const QString generation=readDiskSequence(name);
                        if(!generation.isEmpty() && sequences.value(name)==generation){
                            dev.sequence=generation;
                        }
                        const QString vendor=d.value("vendor").toString().trimmed();
                        if(!vendor.isEmpty())dev.name=vendor+" "+dev.name;
                        for(const auto &entry:d.value("children").toArray()){
                            const auto part=entry.toObject();
                            if(part.value("type").toString()=="part")dev.partitions.append({part.value("path").toString(),part.value("fstype").toString(),usbBytes(part)});
                        }
                        if(dev.name.isEmpty())dev.name="USB drive";
                        // lsblk -b outputs byte counts as JSON numbers or decimal strings.
                        auto sizeVal=d.value("size");
                        bool ok=false;dev.bytes=sizeVal.toVariant().toString().toULongLong(&ok);
                        if(!ok||dev.bytes==0||!dev.path.startsWith("/dev/"))continue;
                        dev.readOnly=d.value("ro").toVariant().toBool();
                        dev.filesystem=d.value("fstype").toString();
                        dev.size=sizeText(dev.bytes);
                        dev.detail=dev.name+" ("+dev.size+") — "+dev.path;
                        const auto children=d.value("children").toArray();
                        int count=usbPartitionCount(d);QStringList parts;
                        for(const auto &c:children){const auto part=c.toObject();if(part.value("type").toString()!="part")continue;
                            const QString fs=part.value("fstype").toString();
                            QStringList mounts;
                            for(const auto &m:part.value("mountpoints").toArray())if(m.isString()&&!m.toString().isEmpty())mounts<<m.toString();
                            if(!mounts.isEmpty())dev.mounted=true;
                            parts<<part.value("name").toString()+" ("+sizeText(part.value("size").toVariant().toString().toULongLong())+")"+
                                (fs.isEmpty()?" · filesystem unknown":" · "+fs)+
                                (mounts.isEmpty()?" · unmounted":" · mounted: "+mounts.join(", "));}
                        dev.detail=dev.detail; dev.partitionSummary=QString::number(count)+" partition(s)"+(parts.isEmpty()?QString():"\n"+parts.join(", "));
                        found<<dev;
                    }
                }
            }
            if(!validSnapshot){
                identityAlert=true;
                baselineRequested=false;
                automaticInitialBaseline=false;
                found.clear();
                recordSafetyEvent(*timedOut ? "lsblk inspection timed out; identity cannot be verified" :
                    "lsblk inspection failed or returned invalid JSON; identity cannot be verified", "critical");
            }
            devices=found;
            QStringList signatures;
            for(const auto &d:devices)signatures << d.path+":"+d.identity;
            signatures.sort();
            const QString currentSignature=signatures.join("|");
            if(lastDeviceSignature!=currentSignature){
                if(lastDeviceSignature.isEmpty() && !currentSignature.isEmpty()){
                    recordSafetyEvent(baselineInitialized ?
                        "USB reconnected or newly detected; comparing with the saved advisory baseline" :
                        "USB detected; read-only inspection available",
                        baselineInitialized?"warning":"info");
                } else if(currentSignature.isEmpty())recordSafetyEvent("USB disconnected or no removable USB detected","critical");
                else recordSafetyEvent("USB device set or reported identity changed; review required","warning");
                lastDeviceSignature=currentSignature;
            }
            // Never silently accept a replacement after a refresh or disconnect.
            if(validSnapshot && !baselineInitialized && devices.size()==1) {baselineInitialized=true;baselineRequested=true;automaticInitialBaseline=true;}
            if(validSnapshot && !baselineInitialized && devices.size()>1){
                recordSafetyEvent("Multiple USB devices detected: automatic identity baseline refused; select the intended device", "warning");
            }
            if(baselineRequested){
                baselineRequested=false;baselineInitialized=true;
                const QString requested=target ? target->currentData().toString() : selectedPath;
                auto it=std::find_if(devices.cbegin(),devices.cend(),[&](const Drive &d){return d.path==requested;});
                // Only the initial automatic baseline may select the first detected drive.
                // Explicit capture MUST NOT silently fall back to another USB.
                if(it==devices.cend() && automaticInitialBaseline && devices.size()==1)it=devices.cbegin();
                automaticInitialBaseline=false;
                if(it!=devices.cend() && !it->identity.isEmpty() && !it->sequence.isEmpty()){
                    baselinePath=it->path;baselineIdentity=it->identity;identityAlert=false;
                    recordSafetyEvent("Advisory identity baseline captured for "+baselinePath,"info");
                }else{identityAlert=true;recordSafetyEvent("Baseline capture refused: selected USB unavailable or identity missing","critical");}
            } else if(!baselinePath.isEmpty()) {
                auto it=std::find_if(devices.cbegin(),devices.cend(),[this](const Drive &d){return d.path==baselinePath;});
                const bool matched=it!=devices.cend() && advisoryBaselineMatches(*it,baselineIdentity);
                if(!matched && !identityAlert)
                    recordSafetyEvent("Baseline drive disconnected or its identity or layout differs","warning");
                if(matched && identityAlert)
                    recordSafetyEvent("USB matches the saved advisory baseline again","info");
                identityAlert=!matched;
            }
            if(identityStatus){
                if(identityAlert || baselinePath.isEmpty()){
                    identityStatus->setText("WARNING  •  Identity changed, missing or unavailable. Review the USB before manually capturing a new baseline. No writes enabled.");
                    identityStatus->setStyleSheet("color:#ffb4a8;font-weight:700;background:#542F45;border:1px solid #D98A98;border-radius:8px;padding:9px;");
                }else{
                    identityStatus->setText("MATCHED  •  Identity baseline verified for "+baselinePath);
                    identityStatus->setStyleSheet("color:#76f5ba;font-weight:700;background:#164F50;border:1px solid #4BAE9D;border-radius:8px;padding:9px;");
                }
            }
            if(safetySummary && safetyDetails){
                QString verdict;
                if(!validSnapshot) verdict="INSPECTION FAILED — USB identity unavailable";
                else if(devices.isEmpty()) verdict="DISCONNECTED — No removable USB detected";
                else if(identityAlert) verdict="WARNING — Identity changed, missing or unavailable";
                else if(baselinePath.isEmpty()) verdict="INSPECTION REQUIRED — No trusted baseline";
                else verdict="MATCHED — Advisory identity comparison only";
                safetySummary->setText(verdict);
                if(lastSafetyState!=verdict){
                    recordSafetyEvent("Safety state: "+verdict,(identityAlert||devices.isEmpty())?"critical":"info");
                    lastSafetyState=verdict;
                }
                safetySummary->setStyleSheet((identityAlert||devices.isEmpty())?
                    "color:#ffb4a8;background:#542F45;border:1px solid #D98A98;border-radius:8px;padding:12px;font-weight:700;":
                    "color:#76f5ba;background:#164F50;border:1px solid #4BAE9D;border-radius:8px;padding:12px;font-weight:700;");
                QStringList lines;
                lines<<"Snapshot source: lsblk (read-only)"<<"Baseline path: "+(baselinePath.isEmpty()?QString("none"):baselinePath)
                     <<"Detected removable USB drives: "+QString::number(devices.size());
                for(const auto &d:devices){
                    lines<<""<<"Device: "+d.path<<"Model: "+d.name<<"Capacity: "+d.size
                         <<"Partition layout: "+d.partitionSummary
                         <<"Read-only flag: "+QString(d.readOnly?"YES":"NO")
                         <<"Mount status: "+(d.mounted?QString("MOUNTED — caution"):QString("No mounts reported"))
                         <<"Matches saved baseline: "+QString(!identityAlert && d.path==baselinePath && d.identity==baselineIdentity?"YES (advisory)":"NO / NOT SELECTED");
                }
                lines<<""<<"Operations revalidate live kernel identity, mounts, swap and holders before accessing the USB.";
                safetyDetails->setText(lines.join("\n"));
            }
            if(target){
                // Avoid destroying the popup while a user is interacting with it.
                if(validSnapshot && target->view() && target->view()->isVisible()){
                    scan=nullptr;p->deleteLater();return;
                }
                const QString previousSequence=target->currentData(Qt::UserRole+2).toString();
                target->blockSignals(true);target->clear();
                target->addItem(devices.isEmpty()?"No USB drives detected":"Select a removable USB drive");
                for(const auto &device:devices){
                    target->addItem(device.detail,device.path);
                    int index=target->count()-1;
                    target->setItemData(index,device.sequence,Qt::UserRole+2);
                    if(device.path==previous && device.sequence==previousSequence)target->setCurrentIndex(index);
                }
                selectedPath=target->currentData().toString();target->blockSignals(false);
            }
            populateOperationChoices();
            if(deviceInfo){
                if(devices.isEmpty())deviceInfo->setText("No USB drives detected.\nConnect a USB drive and refresh.");
                else {
                    auto d=devices.first();
                    deviceInfo->setText("DEVICE  "+d.name+"\nCAPACITY  "+d.size+"     PATH  "+d.path+"\n"+d.partitionSummary+"\nMOUNTS  "+(d.mounted?"Mounted partition present":"None")+"     SOURCE  lsblk");
                }
            }
            status->setText(devices.isEmpty()?"Ready · No USB drive · No disk writes":QString("Ready · %1 USB drive(s) · No disk writes").arg(devices.size()));
            scan=nullptr;p->deleteLater();
        });
        connect(p,&QProcess::errorOccurred,this,[this,p](QProcess::ProcessError){
            if(scan==p){scan=nullptr;devices.clear();identityAlert=true;baselineRequested=false;
                recordSafetyEvent("USB inspection failed — safety warning latched","critical");
                if(identityStatus){identityStatus->setText("WARNING  •  USB scan failed. No device identity can be confirmed.");identityStatus->setStyleSheet("color:#ffb4a8;font-weight:700;background:#542F45;border:1px solid #D98A98;border-radius:8px;padding:9px;");}
                if(target){target->clear();target->addItem("USB detection unavailable");}populateOperationChoices();if(deviceInfo)deviceInfo->setText("USB detection unavailable — check lsblk");status->setText("USB detection unavailable — check lsblk");p->deleteLater();}
        });
        p->start();
    }
};
#ifdef JATAYU_UI_TEST
#include "../tests/studio_ui_test.h"
#endif
int main(int argc,char **argv){
    // Let KDE/Qt supply the native file chooser's style and palette.
    // Studio's visual theme is scoped to its main window stylesheet.
    if(argc==2 && std::strcmp(argv[1],"--version")==0){
        QTextStream(stdout)<<"Jatayu USB Studio "<<studioVersion<<Qt::endl;
        return 0;
    }
    QApplication app(argc,argv);
#ifdef JATAYU_UI_TEST
    return testStudioNavigation(app);
#endif
    app.setApplicationName("Jatayu USB Studio");app.setApplicationVersion(studioVersion);
    if(geteuid()==0){QTextStream(stderr)<<"Run Jatayu USB Studio as an ordinary user."<<Qt::endl;return 1;}
    app.setDesktopFileName("jatayu-usb-studio");app.setWindowIcon(QIcon(":/assets/icon.png"));
    Studio window;window.show();return app.exec();
}
#include "main.moc"
