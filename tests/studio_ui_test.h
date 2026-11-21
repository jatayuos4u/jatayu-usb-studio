int testStudioNavigation(QApplication &app) {
    QTemporaryDir config;
    if(!config.isValid())return 10;
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat,QSettings::UserScope,config.path());
    Studio window;
    window.show();
    app.processEvents();
    auto *pages = window.findChild<QStackedWidget *>("pages");
    const QStringList navigation = {"Home", "Create Bootable USB", "Clone USB", "Format USB",
                                    "Verify USB", "USB Repair", "Device Safety", "Settings", "About", "Downloads"};
    const QHash<int, QStringList> actions = {
        {1, {"Write hybrid Linux ISO", "Create Windows installer (UEFI)", "Inspect USB Write Safety"}},
        {3, {"Format USB"}},
        {4, {"Calculate / Verify SHA-256", "Verify written USB against ISO"}},
        {5, {"Check filesystem health", "Repair filesystem"}},
        {6, {"Run integrated read-only inspection"}}, {9, {"Download ISO"}}
    };
    if (!pages || pages->count() != navigation.size()) return 1;
    for (int index = 0; index < navigation.size(); ++index) {
        QPushButton *button = nullptr;
        for (auto *candidate : window.findChildren<QPushButton *>()) {
            if ((candidate->objectName() == "nav" || candidate->objectName() == "navActive")
                && candidate->text() == navigation[index]) button = candidate;
        }
        if (!button || !button->isVisible()) return 2;
        button->click();
        app.processEvents();
        if (pages->currentIndex() != index || !pages->currentWidget()->isVisible()) return 3;
        for (const auto &name : actions.value(index)) {
            bool enabled = false;
            for (auto *action : pages->currentWidget()->findChildren<QPushButton *>()) {
                if (action->text() == name && action->isEnabled() && action->isVisible()) enabled = true;
            }
            if (!enabled) return 4;
        }
    }
    auto *bootPage=pages->widget(1);
    for(auto *button:bootPage->findChildren<QPushButton *>()){
        if(button->text().contains("advanced diagnostics",Qt::CaseInsensitive) ||
           button->text().startsWith("Simulate USB Writing") ||
           button->text()=="Copy ISO to new file (test)")return 17;
    }
    auto *settings=pages->widget(7);
    QPushButton *developerTools=nullptr, *simulation=nullptr, *copyTest=nullptr;
    for(auto *button:settings->findChildren<QPushButton *>()){
        if(button->text()=="Developer Tools")developerTools=button;
        if(button->text().startsWith("Simulate USB Writing"))simulation=button;
        if(button->text()=="Copy ISO to new file (test)")copyTest=button;
    }
    if(!developerTools || !simulation || !copyTest ||
       simulation->isVisibleTo(settings) || copyTest->isVisibleTo(settings))return 18;
    developerTools->click();
    if(!simulation->isVisibleTo(settings) || !copyTest->isVisibleTo(settings))return 19;
    developerTools->click();
    if(simulation->isVisibleTo(settings) || copyTest->isVisibleTo(settings))return 20;
    auto *refresh=pages->widget(7)->findChild<QCheckBox *>();
    if(!refresh || !refresh->isChecked() || !window.refreshTimer.isActive())return 11;
    refresh->setChecked(false);
    window.preferences.sync();
    const QSettings saved("JatayuOS","Jatayu USB Studio");
    if(window.refreshTimer.isActive() || saved.value("devices/autoRefresh",true).toBool())return 12;
    refresh->setChecked(true);
    if(!window.refreshTimer.isActive())return 13;
    QStringList about;
    for(auto *label:pages->widget(8)->findChildren<QLabel *>())about<<label->text();
    for(const QString &required:QStringList{"Created by Anup Kumar Yadav","Create Bootable USB","Did the simulation write my ISO?","Why was baseline capture refused?"})
        if(!about.contains(required))return 14;
    auto *help=pages->widget(8)->findChild<QTabWidget *>();
    if(!help || help->count()!=3 || help->tabText(0)!="About this tool" || help->tabText(1)!="How to use" || help->tabText(2)!="FAQ")return 15;
    help->setCurrentIndex(2);
    if(help->currentIndex()!=2)return 16;
    bool ntfs = false;
    for (auto *picker : pages->widget(3)->findChildren<QComboBox *>())
        ntfs = ntfs || picker->findData("ntfs") >= 0;
    if (!ntfs) return 6;
    if (!window.windowTitle().contains("v1.1.0 RC1")) return 5;
    Drive first, second;
    first.path="/dev/sdb"; first.sequence="1"; first.bytes=100;
    second.path="/dev/sdc"; second.sequence="2"; second.bytes=200;
    window.devices={first};
    window.populateOperationChoices();
    window.cloneSource->setCurrentIndex(1);
    if(window.cloneDestination->findData(first.path)>=0 || window.cloneStart->isEnabled())return 7;
    window.devices.append(second);
    window.populateOperationChoices();
    window.cloneDestination->setCurrentIndex(window.cloneDestination->findData(second.path));
    if(!window.cloneStart->isEnabled())return 8;
    window.cloneSource->setCurrentIndex(window.cloneSource->findData(second.path));
    if(window.cloneDestination->findData(second.path)>=0 || window.cloneStart->isEnabled())return 9;
    bool mismatchHandled=false;
    QTimer::singleShot(0,&window,[&]{
        auto *dialog=qobject_cast<QDialog *>(QApplication::activeModalWidget());
        if(!dialog)return;
        auto *input=dialog->findChild<QLineEdit *>();
        auto *buttons=dialog->findChild<QDialogButtonBox *>();
        if(!input || !buttons){dialog->reject();return;}
        input->setText("ERASE /dev/wrong");
        buttons->button(QDialogButtonBox::Ok)->click();
        for(auto *label:dialog->findChildren<QLabel *>())
            mismatchHandled|=dialog->isVisible() && label->text().contains("does not match");
        input->setText("ERASE /dev/sdz");
        buttons->button(QDialogButtonBox::Ok)->click();
    });
    if(!window.confirmErase("/dev/sdz","Test confirmation") || !mismatchHandled)return 18;
    Drive reconnected;
    reconnected.identity="same advisory identity";
    for(const QString &generation:QStringList{"17","29"}){
        reconnected.sequence=generation;
        if(!advisoryBaselineMatches(reconnected,"same advisory identity"))return 19;
    }
    if(advisoryBaselineMatches(reconnected,"different advisory identity"))return 20;
    reconnected.sequence.clear();
    if(advisoryBaselineMatches(reconnected,"same advisory identity"))return 21;
    return 0;
}
