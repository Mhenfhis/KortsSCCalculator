# CraftBar.py: Dark Age of Camelot Spellcrafting Calculator 
#
# See http://kscraft.sourceforge.net/ for updates
#
# See NOTICE.txt for copyrights and grant of license

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from B_CraftBar import *
from Character import *
from constants import *
from ScOptions import ScOptions
import os
import os.path
import glob
import re
import string
import SC
import ConfigParser 
import sys

# For pick-daoc default paths, note...
# C:\Mythic\Atlantis
# C:\Mythic\Catacombs
# C:\Mythic\Darkness
# C:\Program Files\Electronic Arts\Labyrinth

class IniConfigParser(ConfigParser.RawConfigParser):
    def __init__(self, defaults=None):
        ConfigParser.RawConfigParser.__init__(self,defaults)

    def write(self, fp):
        """Override whitespace default from RawConfigParser."""
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in self._defaults.items():
                fp.write("%s=%s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for (key, value) in self._sections[section].items():
                if key != "__name__":
                    fp.write("%s=%s\n" %
                             (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")

    def optionxform(self, optionstr):
        """Override lowercase default from RawConfigParser."""
        return optionstr

    
class CraftBar(QDialog, Ui_B_CraftBar):
    def __init__(self,parent = None,name = None,modal = False,fl = Qt.Widget):
        QDialog.__init__(self, parent, fl)
        Ui_B_CraftBar.setupUi(self,self)

        self.model = QStandardItemModel(0, 3)
        self.model.setHeaderData(0, Qt.Horizontal, QVariant('Client'), Qt.DisplayRole)
        self.model.setHeaderData(1, Qt.Horizontal, QVariant('Server'), Qt.DisplayRole)
        self.model.setHeaderData(2, Qt.Horizontal, QVariant('Crafter'), Qt.DisplayRole)
        self.CharList.setModel(self.model)
        self.CharList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.CharList.setShowGrid(False)
        self.CharList.verticalHeader().hide()
        self.CharList.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.CharList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.CharList.setSelectionMode(QAbstractItemView.SingleSelection)

        if (name):
            self.setObjectName(name)
        if (modal):
            self.setModal(modal)

        self.parent = parent
        self.gemcount = 0
        self.piecelist = { }
        self.ItemSelect = [
            self.ChestSelect, self.ArmsSelect, self.HeadSelect,
            self.LegsSelect, self.FeetSelect, self.HandsSelect,
            self.SpareSelect, self.RHSelect, self.LHSelect,
            self.THSelect, self.RangedSelect,
        ]
        self.items = [
            'Chest', 'Arms', 'Head', 'Legs', 'Feet', 'Hands',
            'Spare', 'Right Hand', 'Left Hand', '2 Handed', 'Ranged',
        ]

        self.reini = re.compile('(\w+)-(\d+)\.ini$')
        self.resec = re.compile('\[(\w+)\]')
        self.rectl = re.compile('[Hh]otkey_(\d+)=44,13,')
        
        if str(QApplication.style().objectName()[0:9]).lower() == "macintosh":
            self.PathSelectButton.setFixedWidth(50)
            self.PathSelectButton.setFixedHeight(32)

        self.connect(self.PathSelectButton,SIGNAL("clicked()"),self.openFileDialog)
        self.connect(self.PushButton19,SIGNAL("clicked()"),self.accept)
        self.connect(self.LoadGemsButton,SIGNAL("clicked()"),self.loadGems)
        self.connect(self.DaocPath,SIGNAL("textChanged(const QString&)"),self.findPath)
        self.connect(self.HotbarNum,SIGNAL("valueChanged(int)"),self.hotbarNumChanged)
        self.connect(self.HotbarRow,SIGNAL("valueChanged(int)"),self.hotbarNumChanged)
        self.connect(self.HotbarPos,SIGNAL("valueChanged(int)"),self.hotbarNumChanged)
        self.connect(self.CharList.selectionModel(),SIGNAL("selectionChanged(const QItemSelection&, const QItemSelection&)"),self.charChanged)

        for i in range(0, len(self.ItemSelect)):
            self.connect(self.ItemSelect[i],SIGNAL("clicked()"),self.pieceBoxChanged)
            item = self.parent.itemattrlist[self.items[i]]
            while item.ActiveState == 'drop' and item.next is not None:
                item = item.next
            if item.ActiveState == 'drop':
                self.ItemSelect[i].setEnabled(False)
                continue
            done = True
            unused = True
            for slot in item.slots():
                 if slot.crafted():
                     unused = False
                     if slot.makes() == "0":
                         done = False
                         break
            if unused:
                self.ItemSelect[i].setEnabled(False)
                continue
            if not done and item == self.parent.itemattrlist[self.items[i]]:
                self.ItemSelect[i].setCheckState(Qt.Checked)

        self.HotbarNum.setValue(1)
        self.HotbarRow.setValue(1)
        self.HotbarPos.setValue(1)
        if sys.platform == 'win32':
            path = os.environ.get('APPDATA', '')
            if not os.path.isdir(path):
                path = os.environ.get('HOMEDRIVE', '')
                path = os.path.join(path, os.environ.get('HOMEPATH', ''))
                path = os.path.join(path, 'Application Data')
            path = os.path.join(path, 'Electronic Arts\Dark Age of Camelot')
        else:
            path = os.environ.get('HOME', '')
        self.DaocPath.setText(ScOptions.instance().getOption('DaocIniPath', 
            path))
        self.pieceBoxChanged()
        self.computeGemCount()
        self.computeBarEnd()

    def loadGems(self):
        indexList = self.CharList.selectedIndexes()
        if len(indexList) == 0: return
        for idx in indexList:
            if idx.column() == 0: server = str(idx.data().toString())

        row = indexList[0].row()
        fileIndex = self.model.index(row, 0)
        filename = unicode(self.model.data(fileIndex, Qt.UserRole).toString())
        
        self.LoadGemsButton.setEnabled(0)
        self.LoadGemsButton.update()

        f = open(filename, 'r')
        g = open(filename + '.bak', 'w')
        g.write(f.read())
        f.close()
        g.close()
        CP = IniConfigParser()
        CP.read([filename])
        buttons = [-1, -1, -1]
        newbuttons = []
        slotcounter = 0
        while slotcounter <= 99:
            try:
                buttonstr=CP.get('Macros', 'Macro_%d' % slotcounter)
            except:
                if len(newbuttons) < 3:
                    newbuttons.append(slotcounter)
            else:
                buttonval = string.split(buttonstr, ',', 1)
                if len(buttonval) > 1 and buttonval[1][:7].lower() == '/craft ':
                    if buttonval[1][7].lower() in "ahm":
                        buttons['ahm'.index(buttonval[1][7].lower())] = slotcounter
            slotcounter += 1
        for i in (0, 1, 2):
            if buttons[i] < 0 and len(newbuttons) > 0:
                buttons[i] = newbuttons.pop(0)
                CP.set('Macros', 'Macro_%d' % buttons[i],
                       "%s,/craft %s" % (Realms[i][0:3], Realms[i]))
        
        realm = self.parent.realm
        slotcounter = (self.HotbarNum.value() - 1) * 100 \
                    + (self.HotbarRow.value() - 1) * 10 \
                     + self.HotbarPos.value() - 1
        startslot = slotcounter
        for loc in TabList:
            item = self.piecelist.get(loc, None)
            if item is None: continue
            if item.ActiveState == 'player':
                for slot in item.slots():
                    if slot.crafted():
                        gemname = slot.gemName(realm, 3)
                        if slotcounter >= 300:
                            sys.stdout.write("Out of slots!\n")
                            continue
                        if not HotkeyGems[realm].has_key(gemname):
                            for i in (0, 1, 2):
                                gemname = slot.gemName(Realms[i], 3)
                                if realm == Realms[i]:
                                    continue
                                if HotkeyGems[Realms[i]].has_key(gemname):
                                    realm = Realms[i]
                                    # XXX Huh?  should be the switch realm macro(!)
                                    buttonstr = 'Hotkey_%d' % buttons[i]
                                    if slotcounter >= 200:
                                        CP.set('Quickbar3', 'Hotkey_%d' % slotcounter - 200, buttonstr)
                                    elif slotcounter >= 100:
                                        CP.set('Quickbar2', 'Hotkey_%d' % slotcounter - 100, buttonstr)
                                    else:
                                        CP.set('Quickbar', 'Hotkey_%d' % slotcounter, buttonstr)
                                    slotcounter += 1
                                    break
                        if HotkeyGems[realm].has_key(gemname):
                            val = HotkeyGems[realm][gemname]
                            buttonstr = '45,13%03d%02d,,-1' % (val, slot.gemLevel() - 1)
                            if slotcounter >= 200: 
                                CP.set('Quickbar3', 'Hotkey_%d' % (slotcounter - 200), buttonstr)
                            elif slotcounter >= 100:
                                CP.set('Quickbar2', 'Hotkey_%d' % (slotcounter - 100), buttonstr)
                            else:
                                CP.set('Quickbar', 'Hotkey_%d' % slotcounter, buttonstr)
                            slotcounter += 1
                        else:
                            sys.stdout.write(realm + " has no '" + gemname + "' gem\n")
        f = open(filename, 'w')
        CP.write(f)
        f.close()
        self.LabelNumGems.setText('Number of Quickbar Buttons Loaded:')
        self.NumGems.setText(str(slotcounter - startslot))
        self.HotbarNum.setValue(int(slotcounter / 100) + 1)
        self.HotbarRow.setValue(int(slotcounter / 10) % 10 + 1)
        self.HotbarPos.setValue(slotcounter % 10 + 1)
        self.piecelist = { }
        for ctl in self.ItemSelect:
            if ctl.checkState() == Qt.Checked:
                ctl.setCheckState(Qt.PartiallyChecked)
        self.gemcount = 0
        self.computeBarEnd()

    def findPath(self,rootpath):
        servers = ServerCodes
        if self.parent.euroServers:
            servers = EuroServerCodes
        self.model.removeRows(0, self.model.rowCount())
        rootpath = unicode(rootpath)
        if os.path.isdir(rootpath):
            filelist = glob.glob(rootpath+'/*-*.ini')
            filelist.extend(glob.glob(rootpath+'/*/*-*.ini'))
            filelist.extend(glob.glob(rootpath+'/*/*/*-*.ini'))
            for file in filelist:
                path = file[len(rootpath)+1:]
                slash = path.rfind('/')
                slash = max(slash, path.rfind('\\'))
                m = self.reini.search(path[(slash+1):])
                if slash < 0:
                    path = ''
                else:
                    path = path[:slash]
                if m is None or not servers.has_key(m.group(2)):
                    continue
                # search the section(s) for the pattern
                # [Quickbar[2-3]*]
                # Hotkey_[0-9]*=44,13,
                # corresponding to an SC'er menu quickbar item
                f = open(file, 'r')
                find = 0
                for txt in f:
                    sec = self.resec.match(txt)
                    if sec is not None:
                        if sec.group(1)[:8] == 'Quickbar':
                            find = 1
                        else:
                            find = 0
                        continue
                    if find == 1 and self.rectl.match(txt) is not None:
                        find = 2
                        break
                f.close()
                if find < 2:
                    continue
                server = servers[m.group(2)]
                self.model.insertRows(self.model.rowCount(), 1)
                index = self.model.index(self.model.rowCount()-1, 0, QModelIndex())
                self.model.setData(index, QVariant(path), Qt.DisplayRole)
                self.model.setData(index, QVariant(file), Qt.UserRole)
                index = self.model.index(self.model.rowCount()-1, 1, QModelIndex())
                self.model.setData(index, QVariant(server), Qt.DisplayRole)
                index = self.model.index(self.model.rowCount()-1, 2, QModelIndex())
                self.model.setData(index, QVariant(m.group(1)), Qt.DisplayRole)
                if self.model.rowCount() == 1:
                    self.CharList.selectRow(0)
            if len(filelist) > 0:
                ScOptions.instance().setOption('DaocIniPath', rootpath)
        self.CharList.resizeRowsToContents()

    def openFileDialog(self):
        daocdir = QFileDialog.getExistingDirectory(self, 'Select DAoC Directory', self.DaocPath.text())
        if daocdir:
            self.DaocPath.setText(os.path.abspath(str(daocdir)))

    def computeBarEnd(self):
        pos = (self.HotbarNum.value() - 1) * 100 \
            + (self.HotbarRow.value() - 1) * 10 \
             + self.HotbarPos.value() - 1
        eb = int((pos + self.gemcount - 1) / 100) + 1
        er = int((pos + self.gemcount - 1) / 10) % 10 + 1
        ep = (pos + self.gemcount - 1) % 10 + 1
        if eb > 3 or self.gemcount == 0:
            self.LoadGemsButton.setEnabled(0)
            self.LoadGemsButton.update()
            self.EndBar.setText('-')
            self.EndRow.setText('-')
            self.EndPos.setText('-')
        else:
            self.LoadGemsButton.setEnabled(len(self.CharList.selectedIndexes()) > 0)
            self.LoadGemsButton.update()
            self.EndBar.setText(str(eb))
            self.EndRow.setText(str(er))
            self.EndPos.setText(str(ep))

    def hotbarNumChanged(self,a0):
        self.computeBarEnd()

    def computeGemCount(self):
        self.gemcount = 0
        for loc, item in self.piecelist.items():
            if item.ActiveState == 'player':
                for slot in item.slots():
                    if slot.crafted():
                        self.gemcount += 1
        self.LabelNumGems.setText('Total Number of Gems to Load:')
        self.NumGems.setText(str(self.gemcount))

    def pieceBoxChanged(self):
        self.piecelist = {}
        for i in range(0, len(self.ItemSelect)):
            if self.ItemSelect[i].checkState() == Qt.Checked:
                item = self.parent.itemattrlist[self.items[i]]
                while item.ActiveState == 'drop' and item.next is not None:
                    item = item.next
                self.piecelist[self.items[i]] = item
        self.computeGemCount()
        self.computeBarEnd()

    def charChanged(self, a1, a2):
        self.computeBarEnd()
