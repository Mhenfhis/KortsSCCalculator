# ScWindow.py: Dark Age of Camelot Spellcrafting Calculator (main Window)
#
# See http://kscraft.sourceforge.net/ for updates
#
# See NOTICE.txt for copyrights and grant of license

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from B_ScWindow import *
from Item import *
from Character import *
from constants import *
from xml.dom.minidom import *
from MyStringIO import UnicodeStringIO
from ScOptions import ScOptions
import types
import re
import string
import ItemLevel
import ChooseSlot
import Options
import SC
import CraftWindow
import ReportWindow
import DisplayWindow
import CraftBar
import SearchingCombo
import MultiTabBar
import Ethinarg
import UIXML
import os
import os.path
import ItemList
import time
import locale
import encodings
import codecs
import sys
import binascii

def plainXMLTag(strval):
    i = 0
    while i < len(strval):
        if not (strval[i].isalpha() or (i > 0 and strval[i].isdigit())):
            strval = strval[:i] + strval[i+1:]
        else:
            i += 1
    return strval

class AboutScreen(QDialog):
    def __init__(self,parent = None,name = "About",modal = True,
                 fl = Qt.SplashScreen):
        QDialog.__init__(self,parent,fl)
        self.setModal(modal)
        self.setObjectName(name)
        pixmap = QPixmap(":/images/Spellcraft.png")
        self.palette().setBrush(self.backgroundRole(), QBrush(pixmap))
        self.resize(QSize(480,340).expandedTo(pixmap.size()))
        self.show()
        if not self.hasFocus():
            self.setFocus(Qt.ActiveWindowFocusReason)

    def mouseReleaseEvent(self, e):
        # a little lame, e should match a mouseDown event in our window
        self.close()

    def keyPressEvent(self, e):
        if len(e.text()):
            self.close()


UserEventItemNameUpdatedID = QEvent.Type(QEvent.User + 1)

class UserEventItemNameUpdated(QEvent):
    def __init__(self):
        QEvent.__init__(self, UserEventItemNameUpdatedID)


class ScWindow(QMainWindow, Ui_B_SC):
    def __init__(self):
        ScOptions()
        ScOptions.instance().load()

        self.splashFile = None
        self.ethinargWindow = None
        self.newcount = 0
        self.startup = 1
        self.nocalc = True
        self.recentFiles = []
        self.effectlists = GemLists['All'].copy()
        self.dropeffectlists = DropLists['All'].copy()
        self.itemeffectlists = CraftedLists['All'].copy()

        self.fixedtaborder = False

        QMainWindow.__init__(self,None,Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        Ui_B_SC.setupUi(self,self)
        self.statusBar().hide()
        if str(QApplication.style().objectName()[0:9]).lower() == "macintosh":
            self.sizegrip = QSizeGrip(self)
            self.sizegrip.move(self.width() - 15, self.height() - 15)

        self.initLayout()
        self.initControls()
        self.updateGeometry()
        self.charclass = 'Armsman'

        self.ItemLevelWindow = ItemLevel.ItemLevel(self.window(), '', 1)
        self.loadOptions()
        self.setWindowGeometry()
        self.initMenu()
        self.updateRecentFiles(None)
        self.initialize(False)
        
    def initLayout(self):
        testfont = QFontMetrics(QApplication.font())

        self.switchOnType = {'drop' : [], 'player' : [] }
        self.switchOnType['drop'] = [ 
            self.QualEdit, self.LabelRequirement,
        ]
        self.switchOnType['player'] = [
            self.QualDrop, 
            self.LabelItemCraftTime, self.ItemCraftTime, 
            self.LabelGemMakes, self.LabelGemPoints,
            self.LabelGemCost, self.LabelGemName,
            self.ItemImbueLabel, self.ItemImbue, self.ItemImbueTotal,
            self.ItemOverchargeLabel, self.ItemOvercharge,
            self.ItemCostLabel, self.ItemCost,
            self.ItemPriceLabel, self.ItemPrice,
        ]

        cbwidth = self.CharClass.getMinimumWidth(['Necromancer'])
        itmcbwidth = self.ItemType.getMinimumWidth(['Composite Bow'])
        amtcbwidth = self.QualDrop.getMinimumWidth(['100'])
        # minSizeHint includes one char, test 19.9 width...
        amtedwidth = self.ItemLevel.minimumSizeHint().width()
        amtedwidth += testfont.size(Qt.TextSingleLine, "19.").width()

        if str(QApplication.style().objectName()[0:9]).lower() == "macintosh":
            # mac is including a checkbox/icon width which is absurd
            cbwidth = cbwidth - 14
            itmcbwidth = itmcbwidth - 14
            amtcbwidth = amtcbwidth - 14
            edheight = self.CharName.sizeHint().height() - 1
            cbheight = self.Realm.sizeHint().height()
        else:
            edheight = min(self.CharName.minimumSizeHint().height(),
                           self.Realm.minimumSizeHint().height()) - 2
            cbheight = edheight

        self.CharName.setFixedSize(QSize(cbwidth, edheight))
        self.Realm.setFixedSize(QSize(cbwidth, cbheight))
        self.Realm.insertItems(0, list(Realms))
        self.CharClass.setFixedSize(QSize(cbwidth, cbheight))
        self.CharRace.setFixedSize(QSize(cbwidth, cbheight))
        self.CharLevel.setFixedSize(QSize(amtedwidth, edheight))
        self.CharLevel.setValidator(QIntValidator(0, 99, self))
        self.RealmRank.setFixedSize(QSize(amtedwidth, edheight))
        self.ChampionLevel.setFixedSize(QSize(amtedwidth, edheight))
        self.ChampionLevel.setValidator(QIntValidator(0, 10, self))
        self.CraftTime.setFixedSize(QSize(amtedwidth, edheight))
        self.CraftTime.setValidator(QIntValidator(0, 999, self))
        self.OutfitName.setFixedSize(QSize(cbwidth, cbheight))
        self.OutfitName.setCompleter(None)
        self.GroupCharInfo.layout().setColumnStretch(2, 1)

        self.StatLabel = {}
        self.StatValue = {}
        self.StatCap = {}
        self.StatBonus = {}

        for stat in (DropLists['All']['Stat'] + ('PowerPool', 'Fatigue', 'AF',)):
            self.StatLabel[stat] = getattr(self, stat + 'Label')
            self.StatValue[stat] = getattr(self, stat)
            self.StatCap[stat] = getattr(self, stat + 'Cap')
        width = testfont.size(Qt.TextSingleLine, "CON: ").width()
        self.GroupStats.layout().setColumnMinimumWidth(0,width)
        width = testfont.size(Qt.TextSingleLine, "400").width()
        self.GroupStats.layout().setColumnMinimumWidth(1,width)
        width = testfont.size(Qt.TextSingleLine, " (400)").width()
        self.GroupStats.layout().setColumnMinimumWidth(2,width)

        for stat in (DropLists['All']['Resist']):
            self.StatLabel[stat] = getattr(self, stat + 'Label')
            self.StatValue[stat] = getattr(self, stat)
            self.StatBonus[stat] = getattr(self, stat + 'Cap')
        width = testfont.size(Qt.TextSingleLine, "Energy: ").width()
        self.GroupResists.layout().setColumnMinimumWidth(0,width)
        width = testfont.size(Qt.TextSingleLine, "26").width()
        self.GroupResists.layout().setColumnMinimumWidth(1,width)
        width = testfont.size(Qt.TextSingleLine, " (5)").width()
        self.GroupResists.layout().setColumnMinimumWidth(2,width)

        if str(QApplication.style().objectName()[0:9]).lower() == "macintosh":
            # Mac's text is entirely too compressed, and edit boxes a bit
            # shorter than cbheights.  Adjust some label heights so that we
            # compensate and balance out the display of these grids.
            # Hiding the controls will still hide the grid rows.
            lbheight = self.LabelTotalCost.sizeHint().height() + 5
            self.LabelCharName.setFixedHeight(cbheight)
            self.LabelCharLevel.setFixedHeight(cbheight)
            self.LabelTotalCost.setFixedHeight(lbheight)
            self.LabelTotalPrice.setFixedHeight(lbheight)
            for ctl in self.StatLabel.itervalues():
                ctl.setFixedHeight(lbheight)
            self.LabelTotalUtility.setFixedHeight(lbheight)
            self.LabelCraftTime.setFixedHeight(cbheight)
            self.LabelBonusEdit.setFixedHeight(cbheight)
            self.LabelSpeedEdit.setFixedHeight(cbheight)
            self.LabelDBSource.setFixedHeight(lbheight)

        skillmodel = QStandardItemModel(0,1,self.SkillsList)
        self.SkillsList.setModel(skillmodel)
        skillmodel.insertRows(0, 1)
        index = skillmodel.index(0, 0, QModelIndex())
        skillmodel.setData(index, QVariant("  "), Qt.DisplayRole)
        sksize = self.GroupCharInfo.layout().minimumSize()
        sksize.expandedTo(self.GroupResists.layout().minimumSize())
        self.SkillsList.setSizeHint(sksize)
        self.SkillsList.setMinimumHeight(self.SkillsList.sizeHint().height())
        self.GroupSkillsList.layout().setColumnStretch(0, 1)
        self.ScWinFrame.layout().setColumnStretch(3, 1)

        self.GroupItemFrame.layout().itemAt(0).changeSize(1, 
                                    self.PieceTab.baseOverlap(),
                                    QSizePolicy.Minimum, QSizePolicy.Fixed)
        for tabname in PieceTabList:
            self.PieceTab.addTab(0, qApp.translate("B_SC",tabname,None))
        for tabname in JewelTabList:
            self.PieceTab.addTab(1, qApp.translate("B_SC",tabname,None))
        self.GroupItemFrame.stackUnder(self.PieceTab)
        l = self.ScWinFrame.layout().itemAt(self.ScWinFrame.layout().count()-1)
        l.layout().itemAt(1).changeSize(1, -self.PieceTab.baseOverlap(),
                                        QSizePolicy.Minimum, QSizePolicy.Fixed)

        itemctllayout = self.GroupItemFrame.layout().itemAt(1).layout()
        self.ItemLevel.setFixedSize(QSize(amtedwidth, edheight))
        self.ItemLevel.setValidator(QIntValidator(0, 99, self))
        self.ItemLevelButton.setFixedSize(
            QSize(self.ItemLevelButton.width(), edheight))
        itemctllayout.insertStretch(3, 1)
        self.QualDrop.setFixedSize(QSize(amtcbwidth, cbheight))
        self.QualDrop.insertItems(0, list(QualityValues))
        self.QualEdit.setFixedSize(QSize(amtcbwidth, edheight))
        self.QualEdit.setValidator(QIntValidator(0, 100, self))
        itemctllayout.insertStretch(7, 1)
        self.ItemNameCombo.setFixedHeight(cbheight)
        self.ItemNameCombo.setCompleter(None)

        if str(QApplication.style().objectName()[0:9]).lower() == "macintosh":
            # Force button to be rounded on mac - a rectangular button just
            # looks really weird
            self.ToggleItemView.setFixedHeight(32)
        else:
            self.ToggleItemView.setFixedHeight(cbheight)
        itemctllayout.insertStretch(10, 1)
        itemctllayout.insertStretch(12, 1)

        self.ItemRealm.setFixedSize(QSize(itmcbwidth, cbheight))
        self.ItemType.setFixedSize(QSize(itmcbwidth, cbheight))
        self.ItemSource.setFixedSize(QSize(itmcbwidth, cbheight))
        self.BonusEdit.setFixedSize(QSize(amtedwidth, edheight))
        self.BonusEdit.setValidator(QIntValidator(0, 99, self))
        self.AFDPSEdit.setFixedSize(QSize(amtedwidth, edheight))
        self.SpeedEdit.setFixedSize(QSize(amtedwidth, edheight))
        # Check boxes are about four pixels of whitespace to the right,
        # line this up within the grid.
        self.Offhand.setFixedSize(QSize(self.Offhand.sizeHint().width()-4,
                                        edheight))
        self.DamageType.setFixedSize(QSize(itmcbwidth, cbheight))
        self.LabelItemRequirement.setFixedHeight(edheight)
        self.ItemRequirement.setFixedHeight(edheight)
        width = testfont.size(Qt.TextSingleLine, "Damage: ").width()
        iteminfogrid = self.ItemInfoGrid.layout()
        iteminfogrid.setColumnMinimumWidth(0, width)
        iteminfogrid.setColumnStretch(2, 1)

        self.ClassRestrictionTable.setTabKeyNavigation(False)
        self.ClassRestrictionTable.setFrameStyle(QFrame.NoFrame)
        # The FrameV2 palettes all lie, the OS has control, so make
        # this ClassRestrictionTable object transparent
        palette = QPalette(self.ClassRestrictionTable.palette())
        palette.setColor(QPalette.Base, QColor(0,0,0,0))
        palette.setBrush(QPalette.Base, QBrush(QColor(0,0,0,0)))
        self.ClassRestrictionTable.setPalette(palette)
        self.ClassRestrictionTable.clear()
        testsizewidget = QCheckBox("Necromancer")
        testsizewidget.updateGeometry()
        chkboxwidth = testsizewidget.sizeHint().width() + 4
        item = QListWidgetItem('All')
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Unchecked)
        item.setSizeHint(QSize(chkboxwidth, cbheight))
        self.ClassRestrictionTable.addItem(item)
        for classname in ClassList['All']:
            item = QListWidgetItem(classname)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            item.setSizeHint(QSize(chkboxwidth, cbheight))
            self.ClassRestrictionTable.addItem(item)
        self.ClassRestrictionTable.setFixedWidth(chkboxwidth + \
            self.ClassRestrictionTable.verticalScrollBar().sizeHint().width())
        self.ClassRestrictionTable.updateGeometry()

        self.NoteText.setAcceptRichText(False)
        self.ItemNoteText.setAcceptRichText(False)

        self.GemLabel = []
        self.Type = []
        self.Effect = []
        self.AmountEdit = []
        self.AmountDrop = []
        self.Makes = []
        self.Points = []
        self.Cost = []
        self.Requirement = []
        self.Name = []

        typewidth = self.Type_1.getMinimumWidth(list(DropTypeList))
        effectwidth = self.Effect_1.getMinimumWidth(["Archery and Casting Speed"])
        if str(QApplication.style().objectName()[0:9]).lower() == "macintosh":
            # mac is including a checkbox/icon width which is absurd
            typewidth = typewidth - 14
            effectwidth = effectwidth - 14

        headergrid = self.ItemSlotsHeader.layout()
        itemslotgrid = self.ItemSlotsGrid.layout()
        headergrid.setColumnStretch(8, 1)
        itemslotgrid.setColumnStretch(8, 1)

        width = testfont.size(Qt.TextSingleLine, " Slot 10:").width()
        headergrid.setColumnMinimumWidth(0,width)
        itemslotgrid.setColumnMinimumWidth(0,width)
        headergrid.setColumnMinimumWidth(1,typewidth)
        headergrid.setColumnMinimumWidth(2,amtcbwidth)
        headergrid.setColumnMinimumWidth(3,effectwidth)
        headergrid.setColumnMinimumWidth(4,amtcbwidth)
        reqwidth = amtcbwidth
        width = testfont.size(Qt.TextSingleLine, " Points").width()
        headergrid.setColumnMinimumWidth(5,width)
        itemslotgrid.setColumnMinimumWidth(5,width)
        reqwidth += width
        width = testfont.size(Qt.TextSingleLine, "  999g 00s 00c").width()
        headergrid.setColumnMinimumWidth(6,width)
        itemslotgrid.setColumnMinimumWidth(6,width)
        reqwidth += width
        width = testfont.size(Qt.TextSingleLine, "  ").width()
        headergrid.setColumnMinimumWidth(7,width)
        itemslotgrid.setColumnMinimumWidth(7,width)
        width = testfont.size(Qt.TextSingleLine, 
                  "Owl-runed Stable Enlightening Adamantium Tincture").width()
        #            "Imperfect Mineral Encrusted Nature Spell Stone").width()
        itemslotgrid.setColumnMinimumWidth(8,width)

        # XXX FIX ME - I want to have a decimal!  But Double validator isn't working
        editAmountValidator = QIntValidator(-999, +999, self)

        for i in range(0, 12):
            idx = i + 1

            self.GemLabel.append(getattr(self, 'Gem_Label_%d' % idx))
            self.Type.append(getattr(self, 'Type_%d' % idx))
            self.Type[i].setFixedSize(QSize(typewidth, cbheight))
            self.connect(self.Type[i],SIGNAL("activated(int)"),
                         self.typeChanged)
            self.GemLabel[i].setBuddy(self.Type[i])

            self.AmountEdit.append(getattr(self, 'Amount_Edit_%d' % idx))
            self.AmountEdit[i].setFixedSize(QSize(amtcbwidth, edheight))
            self.AmountEdit[i].setValidator(editAmountValidator)
            self.switchOnType['drop'].append(self.AmountEdit[i])
            self.connect(self.AmountEdit[i],SIGNAL("editingFinished()"),
                         self.amountsChanged)
            #self.connect(self.AmountEdit[i],SIGNAL("textChanged(const QString&)"),
            #             self.amountsChanged)

            self.Effect.append(getattr(self, 'Effect_%d' % idx))
            self.Effect[i].setFixedSize(QSize(effectwidth, cbheight))
            self.Effect[i].setInsertPolicy(QComboBox.NoInsert)
            self.connect(self.Effect[i],SIGNAL("activated(int)"),
                         self.effectChanged)
            self.connect(self.Effect[i],SIGNAL("editTextChanged(const QString&)"),
                         self.effectChanged)

            self.Requirement.append(getattr(self, 'Requirement_%d' % idx))
            self.Requirement[i].setFixedSize(QSize(reqwidth, edheight))
            self.switchOnType['drop'].append(self.Requirement[i])
            self.connect(self.Requirement[i],SIGNAL("editingFinished()"),
                         self.amountsChanged)
            #self.connect(self.Requirement[i],SIGNAL("textChanged(const QString&)"),
            #            self.amountsChanged)

            if i < 6:
                self.AmountDrop.append(getattr(self, 'Amount_Drop_%d' % idx))
                self.AmountDrop[i].setFixedSize(QSize(amtcbwidth, cbheight))
                self.connect(self.AmountDrop[i],SIGNAL("activated(int)"),
                             self.amountsChanged)
                self.Name.append(getattr(self, 'Name_%d' % idx))
                self.switchOnType['player'].extend([
                    self.AmountDrop[i], self.Name[i], ])
            else:
                self.switchOnType['drop'].extend([
                    self.GemLabel[i], self.Type[i], self.Effect[i], ])

            if i < 4:
                self.Makes.append(getattr(self, 'Makes_%d' % idx))
                if str(QApplication.style().objectName()[0:9]).lower() \
                        == "macintosh":
                    self.Makes[i].setFrame(False)
                    self.Makes[i].lineEdit().setFrame(True)
                self.Makes[i].setFixedSize(QSize(amtcbwidth, cbheight))
                self.connect(self.Makes[i],SIGNAL("valueChanged(int)"),
                             self.amountsChanged)
                # Hide '0' values
                self.Makes[i].setSpecialValueText(" ")
                self.Points.append(getattr(self, 'Points_%d' % idx))
                self.Cost.append(getattr(self, 'Cost_%d' % idx))
                self.switchOnType['player'].extend([
                    self.Makes[i], self.Points[i], self.Cost[i], ])

            itemslotgrid.setRowMinimumHeight(i, max(cbheight, edheight))

        self.ItemCraftTime.setFixedSize(QSize(amtcbwidth, edheight))
        self.ItemCraftTime.setValidator(QIntValidator(0, 99, self))

        # Lock the height of ItemSlotsGrid, this is all we need.  Then
        # optimize based on the height of ItemInfoFrame and round it out
        # to the next-multiple of a combobox height.  Scroll the lines
        # by the combobox height, page from the top to bottom slots.
        #
        self.ScrollSlots.setWidgetResizable(False)
        self.ScrollSlots.setWidget(self.ItemSlotsGrid)
        self.ScrollSlots.setRowHeight(cbheight)

        self.ScrollItemInfo.setWidgetResizable(False)
        self.ScrollItemInfo.setWidget(self.ItemInfoGrid)
        self.ScrollItemInfo.setRowHeight(cbheight)
        self.ScrollItemInfo.setMaximumHeight(self.ScrollSlots.maximumHeight())

        # To round this out, we want the ItemSummaryFrame and ItemSlotsFrame
        # to grow first to a maximum of the height of the ScrollSlots plus
        # the height of the labels above.  
        #
        minheight = self.ItemSlotsHeader.sizeHint().height()
        minheight += self.ScrollItemInfo.minimumHeight()
        self.ItemSummaryFrame.setMinimumHeight(minheight)
        self.ItemSlotsFrame.setMinimumHeight(minheight)
        maxheight = self.LabelGemType.sizeHint().height()
        maxheight += self.ScrollSlots.maximumHeight()
        self.ItemSummaryFrame.setMaximumHeight(maxheight)
        self.ItemSlotsFrame.setMaximumHeight(maxheight)

        # Experiments in extracting ItemInfoFrame from the ISF and dropping
        # it into the ItemSlotsFrame, without crashing
        #move = self.ItemSummaryFrame.layout().takeAt(0).widget()
        #move.setParent(self.ItemSlotsFrame)
        #self.ItemSlotsFrame.layout().insertLayout(0, move.layout())

        self.ScWinFrame.updateGeometry()

    def initControls(self):
        # Send these home to the parent form (this QMainWindow), they are dumb QFrames:
        self.GroupStats.mousePressEvent = self.ignoreMouseEvent
        self.GroupResists.mousePressEvent = self.ignoreMouseEvent
        self.GroupItemFrame.mousePressEvent = self.ignoreMouseEvent

        self.connect(self.GroupStats,SIGNAL("mousePressEvent(QMouseEvent*)"),
                     self.mousePressEvent)
        self.connect(self.GroupResists,SIGNAL("mousePressEvent(QMouseEvent*)"),
                     self.mousePressEvent)
        self.connect(self.GroupItemFrame,
                     SIGNAL("mousePressEvent(QMouseEvent*)"),
                     self.mousePressEvent)

        self.connect(self.CharName,SIGNAL("textChanged(const QString&)"),
                     self.templateChanged)
        self.connect(self.Realm,SIGNAL("activated(int)"),
                     self.realmChanged)
        self.connect(self.CharClass,SIGNAL("activated(int)"),
                     self.charClassChanged)
        self.connect(self.CharRace,SIGNAL("activated(int)"),
                     self.raceChanged)
        self.connect(self.CharLevel,SIGNAL("textChanged(const QString&)"),
                     self.totalsChanged)
        # Change these to totalsChanged if Restrictions are finally tested:
        self.connect(self.RealmRank,SIGNAL("textChanged(const QString&)"),
                     self.templateChanged)
        self.connect(self.ChampionLevel,SIGNAL("textChanged(const QString&)"),
                     self.templateChanged)
        self.connect(self.CraftTime,SIGNAL("textChanged(const QString&)"),
                     self.totalsChanged)
        self.connect(self.OutfitName,SIGNAL("activated(int)"), 
                     self.outfitNameSelected)
        self.connect(self.OutfitName,SIGNAL("editTextChanged(const QString&)"),
                     self.outfitNameEdited)

        self.connect(self.PieceTab,SIGNAL("currentChanged"),
                     self.pieceTabChanged)
        self.connect(self.ToggleItemView,SIGNAL("clicked(bool)"),
                     self.toggleItemView)
        self.connect(self.ItemLevel,SIGNAL("textChanged(const QString&)"),
                     self.itemChanged)
        self.connect(self.ItemLevelButton,SIGNAL("clicked()"),
                     self.itemLevelShow)
        self.connect(self.QualDrop,SIGNAL("activated(int)"),
                     self.itemChanged)
        self.connect(self.QualEdit,SIGNAL("textChanged(const QString&)"),
                     self.itemChanged)
        self.connect(self.ItemNameCombo,SIGNAL("activated(int)"),
                     self.itemNameSelected)
        self.connect(self.ItemNameCombo,
                     SIGNAL("editTextChanged(const QString&)"),
                     self.itemNameEdited)
        self.connect(self.Equipped,SIGNAL("stateChanged(int)"),
                     self.itemChanged)
        self.connect(self.ItemCraftTime,SIGNAL("textChanged(const QString&)"),
                     self.itemChanged)
        self.connect(self.ItemRealm,SIGNAL("activated(int)"),
                     self.itemRealmChanged)
        self.connect(self.ItemType,SIGNAL("activated(int)"),
                     self.itemTypeChanged)
        self.connect(self.ItemSource,SIGNAL("activated(int)"),
                     self.itemInfoChanged)
        self.connect(self.AFDPSEdit,SIGNAL("textChanged(const QString&)"),
                     self.itemInfoChanged)
        self.connect(self.BonusEdit,SIGNAL("textChanged(const QString&)"),
                     self.itemInfoChanged)
        self.connect(self.SpeedEdit,SIGNAL("textChanged(const QString&)"),
                     self.itemInfoChanged)
        self.connect(self.Offhand,SIGNAL("stateChanged(int)"),
                     self.itemInfoChanged)
        self.connect(self.DamageType,SIGNAL("activated(int)"),
                     self.itemInfoChanged)
        self.connect(self.ItemRequirement,
                     SIGNAL("textChanged(const QString&)"),
                     self.itemInfoChanged)

        self.connect(self.ClassRestrictionTable, 
                     SIGNAL('itemChanged(QListWidgetItem *)'), 
                     self.classRestrictionsChanged)
        self.connect(self.ItemNoteText,SIGNAL("textChanged()"),
                     self.itemInfoChanged)
        self.connect(self.NoteText,SIGNAL("textChanged()"),
                     self.templateChanged)

        self.connect(self.SkillsList,
                     SIGNAL("activated(const QModelIndex&)"),
                     self.skillClicked)

    def getIcon(self, namebase):
        thisicon = QIcon()
        for size in (16, 24, 32,):
             thisicon.addFile(':/images/normal/' + namebase + str(size) + '.png',
                              QSize(size, size), QIcon.Normal, QIcon.Off)
             thisicon.addFile(':/images/disabled/' + namebase + str(size) + '.png',
                              QSize(size, size), QIcon.Disabled, QIcon.Off)
             thisicon.addFile(':/images/hot/' + namebase + str(size) + '.png',
                              QSize(size, size), QIcon.Active, QIcon.Off)
        return thisicon

    def initMenu(self):
        self.toolbar = QToolBar("Crafting Toolbar")
        self.toolbar.setObjectName("CraftingToolbar")

        self.rf_menu = QMenu('&Recent Files')
        self.connect(self.rf_menu, SIGNAL("triggered(QAction*)"),
                     self.loadRecentFile)
        
        self.filemenu = QMenu('&File', self)
        self.filemenu.addAction('&New', self.newFile,
                                QKeySequence(Qt.CTRL+Qt.Key_N))
        self.toolbar.addAction(self.getIcon('New'), 'New', self.newFile)
        self.filemenu.addAction('&Open...', self.openFile,
                                QKeySequence(Qt.CTRL+Qt.Key_O))
        self.toolbar.addAction(self.getIcon('Open'), 'Open', self.openFile)
        self.filemenu.addAction('&Save', self.saveFile,
                                QKeySequence(Qt.CTRL+Qt.Key_S))
        self.toolbar.addAction(self.getIcon('Save'), 'Save', self.saveFile)
        self.filemenu.addAction('Save &As...', self.saveAsFile)
        self.toolbar.addAction(self.getIcon('SaveAs'), 'Save As',
                               self.saveAsFile)

        self.filemenu.addSeparator()
        self.toolbar.addSeparator()

        self.filemenu.addAction('&Load Item...', self.loadItem,
                                QKeySequence(Qt.CTRL+Qt.SHIFT+Qt.Key_L))
        self.toolbar.addAction(self.getIcon('LoadItem'), 'Load Item', 
                               self.loadItem)
        self.filemenu.addAction('Sa&ve Item...', self.saveItem,
                                QKeySequence(Qt.CTRL+Qt.SHIFT+Qt.Key_S))
        self.toolbar.addAction(self.getIcon('SaveItem'), 'Save Item', 
                               self.saveItem)
        self.filemenu.addAction('Search &Ethinarg\'s Items', self.ethinargTest)
        self.toolbar.addAction(self.getIcon('Search'), 'Search Ethinarg\'s Items',
                               self.ethinargTest)
        self.filemenu.addAction('Item Database Path...', self.chooseItemPath)

        self.filemenu.addSeparator()
        self.toolbar.addSeparator()

        self.filemenu.addAction('Export &Quickbars...', self.openCraftBars)
        self.toolbar.addAction(self.getIcon('ExportGems'), 'Quickbars', 
                               self.openCraftBars)
        self.filemenu.addAction('Export SCTemplate XML...', self.exportAsFile)
        self.filemenu.addAction('Export &UI Window...', self.generateUIXML)
        self.filemenu.addAction('Choose UI Format...', self.chooseXMLUIFile)

        self.filemenu.addSeparator()

        self.filemenu.addMenu(self.rf_menu)
        self.filemenu.addSeparator()
        self.filemenu.addAction('E&xit', self.close,
                                QKeySequence(Qt.CTRL+Qt.Key_X))
        self.menuBar().addMenu(self.filemenu)

        self.movejewelmenu = QMenu('Jewel Slots', self)
        for piece in range(0,len(JewelTabList)):
            act = QAction(JewelTabList[piece], self)
            act.setData(QVariant(piece + len(PieceTabList)))
            self.movejewelmenu.addAction(act)
        self.movepiecemenu = QMenu('Body Slots', self)
        self.swappiecemenu = QMenu('Body Slots', self)
        for piece in range(0,len(PieceTabList)):
            act = QAction(PieceTabList[piece], self)
            act.setData(QVariant(piece))
            self.movepiecemenu.addAction(act)
            act = QAction(PieceTabList[piece], self)
            act.setData(QVariant(piece))
            self.swappiecemenu.addAction(act)
        self.moveitemmenu = QMenu('&Move Item to',self)
        self.swapgemsmenu = QMenu('S&wap Gems with',self)

        # DON'T SWAP OR MOVE TWICE!!!!!!
        #self.connect(self.swapgemsmenu, SIGNAL("triggered(QAction*)"),
        #             self.swapWith)
        self.connect(self.swappiecemenu, SIGNAL("triggered(QAction*)"),
                     self.swapWith)
        #self.connect(self.moveitemmenu, SIGNAL("triggered(QAction*)"),
        #             self.moveTo)
        self.connect(self.movepiecemenu, SIGNAL("triggered(QAction*)"),
                     self.moveTo)
        self.connect(self.movejewelmenu, SIGNAL("triggered(QAction*)"),
                     self.moveTo)

        self.newitemmenu = QMenu('&New Item', self)
        self.chooseitemmenu = QMenu('Item &Type', self)

        self.newitemmenu = QMenu('&New Item', self)
        self.chooseitemmenu = QMenu('Item &Type', self)
        self.connect(self.newitemmenu, SIGNAL("triggered(QAction*)"), 
                     self.newItemType)
        self.connect(self.chooseitemmenu, SIGNAL("triggered(QAction*)"), 
                     self.chooseItemType)

        self.editmenu = QMenu('&Edit', self)
        self.chooseitemmenuid = self.editmenu.addMenu(self.chooseitemmenu)
        self.swapgemsmenuid = self.editmenu.addMenu(self.swapgemsmenu)

        self.editmenu.addSeparator()

        self.editmenu.addMenu(self.newitemmenu)
        self.editmenu.addMenu(self.moveitemmenu)
        self.editmenu.addAction('Delete Item', self.deleteCurrentItem)
        self.editmenu.addAction('Clear Item', self.clearCurrentItem)
        self.editmenu.addAction('Clear Slots', self.clearCurrentItemSlots)

        self.editmenu.addSeparator()

        self.editmenu.addAction('Ne&w Outfit', self.newOutfit)
        self.deleteOutfitAction = self.editmenu.addAction('Delete Outfit', self.deleteOutfit)

        self.editmenu.addSeparator()

        self.editmenu.addAction('&Options...', self.openOptions,
                                QKeySequence(Qt.ALT+Qt.Key_O))

        self.menuBar().addMenu(self.editmenu)

        self.viewmenu = QMenu('&View', self)
        self.craftingmenuid = self.viewmenu.addAction('Craft &Gems',
                                  self.openCraftWindow,
                                  QKeySequence(Qt.ALT+Qt.Key_G))
        self.craftingtoolid = self.toolbar.addAction(self.getIcon('CraftGems'),
                                  'Craft Gems', self.openCraftWindow)

        self.viewmenu.addSeparator()

        self.viewmenu.addAction('&Materials Report', self.openMaterialsReport,
                                QKeySequence(Qt.ALT+Qt.Key_M))
        self.toolbar.addAction(self.getIcon('MatsReport'), 'Materials Report',
                               self.openMaterialsReport)
        self.viewmenu.addAction('&Configuration Report', self.openConfigReport,
                                QKeySequence(Qt.ALT+Qt.Key_C))
        self.toolbar.addAction(self.getIcon('ConfReport'), 'Configuration Report',
                               self.openConfigReport)
        self.viewmenu.addAction('Choose Config Template...',
                                self.chooseReportFile)

        self.viewmenu.addSeparator()

        self.viewtoolbarmenu = QMenu('&Toolbar', self)
        for (title, res) in (("Large", 32,), ("Normal", 24,),
                             ("Tiny", 16,),  ("Hide", 0,),):
            act = QAction(title, self)
            act.setData(QVariant(res))
            act.setCheckable(True)
            self.viewtoolbarmenu.addAction(act)
        self.viewtoolbarmenu.actions()[1].setChecked(True)
        self.connect(self.viewtoolbarmenu, SIGNAL("triggered(QAction*)"), 
                     self.viewToolbar)
        self.viewmenu.addMenu(self.viewtoolbarmenu)

        self.viewmenu.addSeparator()

        self.showcapmenuid = self.viewmenu.addAction('&Distance to Cap',
                                 self.showCap, QKeySequence(Qt.ALT+Qt.Key_D))
        self.showcapmenuid.setCheckable(True)
        self.showcapmenuid.setChecked(self.capDistance)
        self.menuBar().addMenu(self.viewmenu)

        self.errorsmenu = QMenu('Errors', self)
        self.errorsmenuid = self.menuBar().addMenu(self.errorsmenu)
        self.connect(self.errorsmenu, SIGNAL('triggered(QAction*)'), 
                     self.changePieceTab)
        self.helpmenu = QMenu('&Help', self)
        self.helpmenu.addAction('&About', self.aboutBox)
        self.menuBar().addMenu(self.helpmenu)

        self.addToolBar(self.toolbar)
        state = ScOptions.instance().getOption('WindowState', None)
        if state:
            self.restoreState(binascii.a2b_base64(state), 0)
            iconsz = ScOptions.instance().getOption('ToolbarSize', 16)
            if self.toolbar.isHidden():
                iconsz = 0
            for act in self.viewtoolbarmenu.actions():
                if act.data().toInt()[0] == iconsz:
                    act.setChecked(True)
                else:
                    act.setChecked(False)
            if iconsz != 0:
                self.setIconSize(QSize(iconsz, iconsz))

    def fix_taborder(self, line):
        if line > 0:
            prev = self.Requirement[line - 1]
        else: 
            prev = self.NoteText
        for i in range(line, 12):
            # Create the (sometimes used) edit boxes
            self.setTabOrder(prev,self.Type[i])
            self.setTabOrder(self.Type[i],self.AmountEdit[i])
            if i < 6:
                self.setTabOrder(self.AmountEdit[i],self.AmountDrop[i])
                self.setTabOrder(self.AmountDrop[i],self.Effect[i])
                if i < 4:
                    self.setTabOrder(self.Effect[i],self.Makes[i])
                    self.setTabOrder(self.Makes[i],self.Requirement[i])
                else:
                    self.setTabOrder(self.Effect[i],self.Requirement[i])
            else:
                self.setTabOrder(self.AmountEdit[i],self.Effect[i])
                self.setTabOrder(self.Effect[i],self.Requirement[i])
            prev = self.Requirement[i]
        self.setTabOrder(prev, self.ItemCraftTime)

    def showFixWidgets(self):
        for i in range(0,6):
            self.GemLabel[i].setText('Slot &%d:' % (i + 1))
            self.GemLabel[i].show()
            self.Type[i].show()
            self.Effect[i].show()

    def showDropWidgets(self, item):
        if not self.isVisible(): return
        self.GroupItemFrame.hide()
        self.showFixWidgets()
        for w in self.switchOnType['player']:
            w.hide()
        for w in self.switchOnType['drop']:
            w.show()
        #self.GroupItemFrame.updateGeometry()
        self.GroupItemFrame.show()

    def showPlayerWidgets(self, item):
        self.GroupItemFrame.hide()
        self.showFixWidgets()
        for w in self.switchOnType['drop']:
            w.hide()
        for w in self.switchOnType['player']:
            w.show()
        for i in range(0,item.slotCount()):
            if item.slot(i).slotType() == 'player':
                self.GemLabel[i].setText('Gem &%d:' % (i + 1))
            else:
                if i < 4:
                    self.Makes[i].hide()
                    self.Points[i].hide()
                    self.Cost[i].hide()
                self.Requirement[i].show()
            if item.slot(i).slotType() == 'unused':
                if item.slot(i).type() == 'Unused':
                    self.GemLabel[i].hide()
                    self.Type[i].hide()
                    self.AmountDrop[i].hide()
                    self.Effect[i].hide()
                    self.Requirement[i].hide()
        self.GroupItemFrame.show()

    def closeEvent(self, e):
        if self.ethinargWindow:
            self.ethinargWindow.close()

        self.saveOptions()
        ScOptions.instance().save()
        if self.modified:
            ret = QMessageBox.warning(self, 'Save Changes?', 
                                      "This template has been changed.\n"
                                      "Do you want to save these changes?", 
                                      QMessageBox.Yes, QMessageBox.No,
                                      QMessageBox.Cancel)
            if ret == QMessageBox.Cancel:
                e.ignore()
                return
            if ret == QMessageBox.Yes:
                self.saveFile()
                if self.modified: 
                    e.ignore()
                    return
        e.accept()

    def setWindowGeometry(self):
        x = ScOptions.instance().getOption('WindowX', self.pos().x())
        y = ScOptions.instance().getOption('WindowY', self.pos().y())
        w = ScOptions.instance().getOption('WindowW', self.width())
        h = ScOptions.instance().getOption('WindowH', self.height())

        screenW = QApplication.desktop().width()
        screenH = QApplication.desktop().height()
        if w < 100:
            w = 781
        if h < 100:
            w = 589

        if w > screenW:
            w = 781
        if h > screenH:
            h = 589

        if x < 0 or x > (screenW - w):
            x = 20
        if y < 0 or y > (screenH - h):
            y = 20

        self.resize(w, h)
        self.move(x, y)
        self.updateGeometry()
        
    def loadOptions(self):
        self.realm = ScOptions.instance().getOption('Realm', 'Albion')
        self.crafterSkill = ScOptions.instance().getOption('CrafterSkill', 1000)
        self.showDoneInMatsList = ScOptions.instance().getOption('DontShowDoneGems', False)
        self.includeRacials = ScOptions.instance().getOption('IncludeRRInRacials', False)
        self.capDistance = ScOptions.instance().getOption('DistanceToCap', False)
        self.hideNonClassSkills = ScOptions.instance().getOption('HideNonClassSkills', False)
        self.euroServers = ScOptions.instance().getOption('EuroServers', False)
        self.coop = ScOptions.instance().getOption('Coop', False)
        self.pricingInfo = ScOptions.instance().getOption('Pricing', {})
        self.recentFiles = ScOptions.instance().getOption('RecentFiles', [])
        self.ItemPath = ScOptions.instance().getOption('ItemPath',
            os.path.join(os.path.dirname(
                os.path.abspath(sys.argv[0])), "items"))
        self.TemplatePath = ScOptions.instance().getOption('TemplatePath',
            os.path.join(os.path.dirname(
                os.path.abspath(sys.argv[0])), "templates"))
        self.ReportPath = ScOptions.instance().getOption('ReportPath',
            os.path.join(os.path.dirname(
                os.path.abspath(sys.argv[0])), "reports"))
        self.ReportFile = ScOptions.instance().getOption('ConfigReportXSLT',
            os.path.join(self.ReportPath, 'DefaultConfigReport.xsl'))
        self.UiReportFile = ScOptions.instance().getOption('ConfigUiReportXSLT',
            os.path.join(self.ReportPath, 'DefaultUiXmlWindow.xsl'))
        self.toggleItemView(ScOptions.instance().getOption('CurrentItemFrame',
            'ItemSlotsFrame'))
        if not self.pricingInfo.has_key('Tier') or\
                not isinstance(self.pricingInfo['Tier'], dict):
            self.pricingInfo['Tier'] = {}
            ScOptions.instance().setOption('Pricing', self.pricingInfo)
        maximized = ScOptions.instance().getOption('Maximized', False)
        if maximized and sys.platform == 'win32':
            self.setWindowState(Qt.WindowMaximized)
        sizepolicy = QSizePolicy(self.GroupItemFrame.sizePolicy())
        if (ScOptions.instance().getOption('ShowScrollingSlots', True)):
            sizepolicy.setVerticalPolicy(QSizePolicy.Preferred)
        else:
            sizepolicy.setVerticalPolicy(QSizePolicy.Minimum)
        self.GroupItemFrame.setSizePolicy(sizepolicy)

    def saveOptions(self):
        ScOptions.instance().setOption('Realm', self.realm)
        ScOptions.instance().setOption('RecentFiles', self.recentFiles)
        ScOptions.instance().setOption('ItemPath', self.ItemPath)
        ScOptions.instance().setOption('TemplatePath', self.TemplatePath)
        ScOptions.instance().setOption('ReportPath', self.ReportPath)
        ScOptions.instance().setOption('ConfigReportXSLT', self.ReportFile)
        ScOptions.instance().setOption('ConfigUiReportXSLT', self.UiReportFile)

        maximized = self.isMaximized() and sys.platform == 'win32'

        if not maximized:
            ScOptions.instance().setOption('WindowX', self.pos().x())
            ScOptions.instance().setOption('WindowY', self.pos().y())
            ScOptions.instance().setOption('WindowW', self.width())
            ScOptions.instance().setOption('WindowH', self.height())

        ScOptions.instance().setOption('Maximized', maximized)

        ScOptions.instance().setOption('WindowState', 
            binascii.b2a_base64(self.saveState(0))[:-1])
        ScOptions.instance().setOption('ToolbarSize',
            self.iconSize().width())
        ScOptions.instance().setOption('CurrentItemFrame',
            self.stackedlayout.currentWidget().objectName())

    def initialize(self, moretodo):
        self.nocalc = True
        self.NoteText.setPlainText('')
        self.filename = None
        self.newcount = self.newcount + 1
        filetitle = unicode("Template" + str(self.newcount))
        self.setWindowTitle(filetitle + " - Kort's Spellcrafting Calculator")

        self.PieceTab.setCurrentIndex(0, 0)
        self.currentTab = self.PieceTab
        self.currentTabLabel = string.strip(str(self.PieceTab.tabText(0, 0)))

        self.outfitnumbering = 1
        self.currentOutfit = 0
        self.outfitlist = []
        self.OutfitName.clear()
        self.deleteOutfitAction.setEnabled(False)

        self.itemIndex = 0
        self.itemattrlist = { }
        self.itemnumbering = 1

        for tab in PieceTabList:
            item = Item('player', tab, self.realm, self.itemIndex)
            self.itemIndex += 1
            item.next = Item('drop', tab, self.realm, self.itemIndex)
            self.itemIndex += 1
            item.ItemName = "Crafted Item" + str(self.itemnumbering)
            item.next.ItemName = "Drop Item" + str(self.itemnumbering)
            self.itemnumbering += 1
            self.itemattrlist[tab] = item
        for tab in JewelTabList:
            item = Item('drop', tab, self.realm, self.itemIndex)
            self.itemIndex += 1
            item.ItemName = "Drop Item" + str(self.itemnumbering)
            self.itemnumbering += 1
            self.itemattrlist[tab] = item

        self.CharName.setText('')
        self.Realm.setCurrentIndex(Realms.index(self.realm))
        self.realmChanged(Realms.index(self.realm))
        self.CharLevel.setText('50')
        self.RealmRank.setText('1L1')
        self.ChampionLevel.setText('0')
        self.CraftTime.setText('0')
        self.appendOutfit()
        self.restoreItem(self.itemattrlist[self.currentTabLabel])
        self.modified = False
        self.nocalc = moretodo
        if self.nocalc: return
        self.calculate()

    def asXML(self, rich=False):
        document = Document()
        rootnode = document.createElement('SCTemplate')
        document.appendChild(rootnode)
        childnode = document.createElement('Name')
        childnode.appendChild(document.createTextNode(
                                       unicode(self.CharName.text())))
        rootnode.appendChild(childnode)
        childnode = document.createElement('Realm')
        childnode.appendChild(document.createTextNode(self.realm))
        rootnode.appendChild(childnode)
        childnode = document.createElement('Class')
        childnode.appendChild(document.createTextNode(self.charclass))
        rootnode.appendChild(childnode)
        childnode = document.createElement('Race')
        childnode.appendChild(document.createTextNode(
                                       unicode(self.CharRace.currentText())))
        rootnode.appendChild(childnode)
        childnode = document.createElement('Level')
        childnode.appendChild(document.createTextNode(
                                       unicode(self.CharLevel.text())))
        rootnode.appendChild(childnode)
        childnode = document.createElement('RealmRank')
        childnode.appendChild(document.createTextNode(
                                       unicode(self.RealmRank.text())))
        rootnode.appendChild(childnode)
        childnode = document.createElement('ChampionLevel')
        childnode.appendChild(document.createTextNode(
                                       unicode(self.ChampionLevel.text())))
        rootnode.appendChild(childnode)
        rootnode.appendChild(childnode)
        childnode = document.createElement('CraftTime')
        childnode.appendChild(document.createTextNode(
                                       unicode(self.CraftTime.text())))
        rootnode.appendChild(childnode)
        childnode = document.createElement('Notes')
        childnode.appendChild(document.createTextNode(
                                  unicode(self.NoteText.toPlainText())))
        rootnode.appendChild(childnode)

        if rich:
            totalsdict = self.summarize()
            for key in (u'Cost', u'Price', u'Utility',):
                val = totalsdict[key]
                childnode = document.createElement(key)
                childnode.appendChild(document.createTextNode(unicode(val)))
                rootnode.appendChild(childnode)
            for key in (u'Stats', u'Resists', u'Skills', u'Focus', 
                        u'OtherBonuses', u'PvEBonuses'):
                if key == 'Stats':
                    types = DropLists['All']['Stat'] + ('% Power Pool', 'Fatigue', 'AF')
                elif key == 'Resists':
                    types = DropLists['All']['Resist']
                else:
                    types = totalsdict[key].keys()
                    types.sort()
                childnode = document.createElement(key)
                if key[-7:] == 'Bonuses':
                    childnode.setAttribute(u'text', key[:-7] + u' ' + key[-7:])
                for type in types:
                    tagname = unicode(plainXMLTag(type))
                    effectnode = document.createElement(tagname)
                    if tagname != type:
                        effectnode.setAttribute(u'text', unicode(type))
                    if key == 'Stats':
                        subs = (u'Bonus', u'TotalBonus', u'BaseCap', 
                                u'CapBonus', u'TotalCapBonus', 
                                u'BaseCapToCapBonus',) 
                    else:
                        subs = (u'Bonus', u'TotalBonus', u'BaseCap',)
                        if key == u'Resists' and \
                                totalsdict[key][type].has_key('RacialBonus'): 
                            subs = subs + ('RacialBonus',)
                    for subtype in subs:
                        tagname = unicode(plainXMLTag(subtype))
                        valnode = document.createElement(tagname)
                        if tagname != subtype:
                            effectnode.setAttribute(u'text', unicode(subtype))
                        val = unicode(totalsdict[key][type][subtype])
                        valnode.appendChild(document.createTextNode(val))
                        effectnode.appendChild(valnode)
                    childnode.appendChild(effectnode)
                rootnode.appendChild(childnode)

        for key in TabList:
            item = self.itemattrlist[key]
            # use firstChild here because item.asXML() constructs a Document()
            while item is not None:
                childnode = item.asXML(self.pricingInfo, self.crafterSkill, 
                                       self.realm, rich, True)
                if childnode is not None:
                    rootnode.appendChild(childnode.firstChild)
                item = item.next

        for idx in range(0, len(self.outfitlist)):
            outfit = self.outfitlist[idx]
            outfitnode = document.createElement('Outfit')
            outfitnode.setAttribute(u'Name', outfit[None])
            outfitnode.setAttribute(u'Active', unicode(int(idx == self.currentOutfit)))
            for piece, item in outfit.iteritems():
                if piece is None: continue
                piecenode = document.createElement('OutfitItem')
                piecenode.setAttribute('Location', piece)
                piecenode.setAttribute('Index', unicode(item[0]))
                piecenode.setAttribute('Equipped', unicode(item[1]))
                outfitnode.appendChild(piecenode)
            rootnode.appendChild(outfitnode)

        return document

    def slotUpdateMenus(self):
        self.newitemmenu.clear()
        act = QAction('Drop Item', self)
        act.setData(QVariant('Drop Item'))
        self.newitemmenu.addAction(act)

        if self.currentTabLabel in JewelTabList:
            moveactionlist = self.movejewelmenu.actions()
            movesubmenu = self.movepiecemenu
            craftedslot = False
            crafteditem = False
        else:
            swapactionlist = self.swappiecemenu.actions()
            moveactionlist = self.movepiecemenu.actions()
            movesubmenu = self.movejewelmenu
            craftedslot = True
            crafteditem = (
                self.itemattrlist[self.currentTabLabel].ActiveState == 'player')
        self.moveitemmenu.clear()
        for act in moveactionlist:
            if str(act.text()) == self.currentTabLabel: continue
            self.moveitemmenu.addAction(act)
        if not crafteditem:
            self.moveitemmenu.addSeparator()
            self.moveitemmenu.addMenu(movesubmenu)

        self.chooseitemmenuid.setEnabled(crafteditem)
        self.swapgemsmenuid.setEnabled(crafteditem)
        if not craftedslot:
            return

        self.swapgemsmenu.clear()
        for act in swapactionlist:
            if str(act.text()) == self.currentTabLabel: continue
            self.swapgemsmenu.addAction(act)

        itemtypes = ['Normal Item',]
        if (self.currentTabLabel in PieceTabList[:6] 
         or self.currentTabLabel == PieceTabList[-1]):
            itemtypes.append('Enhanced Armor')
        if self.currentTabLabel in PieceTabList[6:]:
            itemtypes.extend(('Caster Staff', 'Legendary Staff',
                              'Enhanced Bow', 'Legendary Bow',
                              'Legendary Weapon', 'Enhanced Sheild', 
                              'Enhanced Harp', 'Enhanced Weapon'))
        self.newitemmenu.addSeparator()
        self.chooseitemmenu.clear()
        for type in itemtypes:
            act = QAction(type, self)
            act.setData(QVariant(type))
            self.newitemmenu.addAction(act)
            act = QAction(type, self)
            act.setData(QVariant(type))
            self.chooseitemmenu.addAction(act)

    def pieceTabChanged(self, row, col):
        self.currentTabLabel = string.strip(str(self.PieceTab.tabText(row,col)))
        if self.nocalc:
            return
        self.restoreItem(self.itemattrlist[self.currentTabLabel])

    def changePieceTab(self,a0):
        mask = a0.data().toInt()[0]
        row = (mask >> 8) & 0xff
        col = mask & 0xff
        self.PieceTab.setCurrentIndex(row, col)

    def fixupItemLevel(self):
        if str(self.ItemLevel.text()) == '' \
                or re.compile('\D').search(str(self.ItemLevel.text())):
            itemimbue = 0
        else:
            itemlevel = int(str(self.ItemLevel.text()))
            if itemlevel > 51: itemlevel = 51
            if itemlevel < 1: itemlevel = 1
            self.ItemLevel.setText('%d' % itemlevel)

    def itemTypeChanged(self, a0=None, item=None):
        if item is None: 
            if self.nocalc:
                return
            item = self.itemattrlist[self.currentTabLabel]
            item.TYPE = unicode(self.ItemType.currentText())
            self.modified = True

        isarmor = (item.TYPE in ItemTypes['Chest'][item.Realm])
        isweapon = ((item.TYPE in ItemTypes['Left Hand'][item.Realm])
                 or (item.TYPE in ItemTypes['2 Handed'][item.Realm])
                 or (item.TYPE in ItemTypes['Ranged'][item.Realm]))
        notoffhand = ((item.TYPE in ItemTypes['Ranged'][item.Realm])
                   or (((item.TYPE in ItemTypes['2 Handed'][item.Realm])
                     or (item.TYPE in ItemTypes['Left Hand'][item.Realm]))
                   and (item.TYPE not in ItemTypes['Right Hand'][item.Realm])))
        isinstrument = ((item.TYPE in ItemTypes['Ranged'][item.Realm])
                    and (item.TYPE in ItemTypes['2 Handed'][item.Realm]))

        if item.ActiveState == 'drop':
            damagetypes = list(DropLists['All']['Resist'])
        else:
            damagetypes = ['Slash', 'Crush', 'Thrust']
        if isweapon:
            self.LabelAFDPSEdit.setText('DPS: ')
        else:
            damagetypes = ['']
            if isarmor:
                self.LabelAFDPSEdit.setText('AF: ')

        if item.DAMAGETYPE not in damagetypes:
            damagetypes.append(item.DAMAGETYPE)
        self.DamageType.clear()
        self.DamageType.insertItems(0, damagetypes)
        self.DamageType.setCurrentIndex(damagetypes.index(item.DAMAGETYPE))
        self.AFDPSEdit.setText(item.AFDPS)
        self.BonusEdit.setText(item.Bonus)
        self.SpeedEdit.setText(item.Speed)
        if item.OFFHAND == 'yes':
            self.Offhand.setCheckState(Qt.Checked)
        else:
            self.Offhand.setCheckState(Qt.Unchecked)

        self.LabelSpeedEdit.setVisible(isweapon and not isinstrument)
        self.SpeedEdit.setVisible(isweapon and not isinstrument)
        self.LabelAFDPSEdit.setVisible((isweapon or isarmor) 
                                       and not isinstrument)
        self.AFDPSEdit.setVisible((isweapon or isarmor)
                                  and not isinstrument)
        self.Offhand.setVisible(isweapon and not notoffhand)
        self.LabelDamageType.setVisible(isweapon)
        self.DamageType.setVisible(isweapon)
        self.ScrollItemInfo.bestFit()
        self.ScrollItemInfo.setMaximumHeight(self.ScrollSlots.maximumHeight())

    def itemRealmChanged(self, a0=None, item=None):
        if item is None: 
            if self.nocalc:
                return
            item = self.itemattrlist[self.currentTabLabel]
            item.Realm = unicode(self.ItemRealm.currentText())
            self.modified = True
        itemtypes = ItemTypes[self.currentTabLabel]
        if isinstance(itemtypes, dict):
            itemtypes = itemtypes[item.Realm]
        if a0 is not None:
            if self.ItemType.currentIndex() < len(itemtypes):
                item.TYPE = itemtypes[self.ItemType.currentIndex()]
            else:
                item.TYPE = itemtypes[0]
        elif item.TYPE not in itemtypes and len(item.TYPE) > 0:
            itemtypes = list(itemtypes) + [item.TYPE,]
        self.ItemType.clear()
        self.ItemType.insertItems(0, itemtypes)
        if len(item.TYPE) > 0:
            self.ItemType.setCurrentIndex(itemtypes.index(item.TYPE))
        else:
            item.TYPE = itemtypes[0]
        self.itemTypeChanged(item=item)
        self.displayClassRestrictions(item)

    def restoreItem(self, item):
        if item is None: return
        wasnocalc = self.nocalc
        self.nocalc = True
        itemtype = item.ActiveState
        if itemtype == 'player':
            self.showPlayerWidgets(item)
        else:
            self.showDropWidgets(item)

        self.ItemLevel.setText(item.Level)
        if itemtype == 'drop':
            self.QualEdit.setText(item.ItemQuality)
        else:
            if item.ItemQuality in QualityValues:
                self.QualDrop.setCurrentIndex(
                    QualityValues.index(item.ItemQuality))

        self.ItemNameCombo.clear()
        altitem = item
        while altitem is not None:
            self.ItemNameCombo.addItem(altitem.ItemName)
            altitem = altitem.next
        self.ItemNameCombo.setCurrentIndex(0)

        self.Equipped.setChecked(int(item.Equipped))
        self.ItemCraftTime.setText(item.Time)

        if itemtype == 'drop':
            realms = AllRealms
            sources = ['Drop', 'Quest', 'Artifact', 'Merchant', 'Unique',]
        else:
            realms = Realms
            sources = ['Crafted']

        self.ItemRealm.clear()
        self.ItemRealm.insertItems(0, realms)
        if item.Realm not in realms:
            item.Realm = self.realm
        self.ItemRealm.setCurrentIndex(realms.index(item.Realm))

        self.ItemSource.clear()
        self.ItemSource.insertItems(0, sources)
        sourceindex = self.ItemSource.findText(item.SOURCE, Qt.MatchExactly)
        if sourceindex >= 0:
            self.ItemSource.setCurrentIndex(sourceindex)
        else:
            item.SOURCE = unicode(self.ItemSource.currentText())

        self.itemRealmChanged(item=item)

        self.ItemRequirement.setText(item.Requirement)
        self.DBSource.setText(item.DBSOURCE)
        self.ItemNoteText.setPlainText(item.Notes)

        for slot in range(0, item.slotCount()):
            typecombo = self.Type[slot]
            typecombo.clear()
            if itemtype == 'player':
                if item.slot(slot).slotType() == 'player':
                    typelist = list(TypeList)
                elif item.slot(slot).slotType() == 'effect':
                    typelist = list(EffectTypeList)
                else:
                    typelist = list(CraftedTypeList)
            else:
                typelist = list(DropTypeList)
            gemtype = str(item.slot(slot).type())
            if ('Focus' in typelist 
            and (item.Location not in FocusTabList 
              or (self.hideNonClassSkills
              and len(AllBonusList[self.realm][self.charclass]['Focus Hash']) == 0))):
                    typelist.remove('Focus')
            if not gemtype in typelist:
                typelist.append(gemtype)

            typecombo.insertItems(0, typelist)
            typecombo.setCurrentIndex(typelist.index(gemtype))
            self.typeChanged(typelist.index(gemtype), slot)

            gemeffect = str(item.slot(slot).effect())
            effect = self.Effect[slot].findText(gemeffect)
            if len(gemeffect) and effect < 0:
                if itemtype == 'player':
                    self.Effect[slot].addItem(gemeffect)
                    self.Effect[slot].setCurrentIndex(
                                          self.Effect[slot].count() - 1)
                    self.effectChanged(effect, slot)
                else:
                    if not self.Effect[slot].isEditable():
                        self.Effect[slot].setEditable(True)
                    self.Effect[slot].setEditText(gemeffect)
            else:
                self.Effect[slot].setCurrentIndex(effect)
                self.effectChanged(effect, slot)
            if itemtype == 'drop':
                self.AmountEdit[slot].setText(item.slot(slot).amount())
            else:
                gemamount = item.slot(slot).amount()
                amount = self.AmountDrop[slot].findText(gemamount)
                if len(gemamount) and gemamount != "0" and amount < 0:
                    self.AmountDrop[slot].addItem(gemamount)
                    self.AmountDrop[slot].setCurrentIndex(
                                              self.AmountDrop[slot].count() - 1)
                else:
                    self.AmountDrop[slot].setCurrentIndex(amount)
            if itemtype == 'player' and item.slot(slot).slotType() == 'player':
                self.Makes[slot].setValue(int(item.slot(slot).makes()))
            else:
                self.Requirement[slot].setText(item.slot(slot).requirement())
        self.slotUpdateMenus()
        self.nocalc = wasnocalc
        if self.nocalc: return
        self.calculate()

    def toggleItemView(self, frame=None):
        if not isinstance(frame,basestring):
            if self.stackedlayout.currentWidget().objectName() == "ItemSlotsFrame":
                frame = "ItemSummaryFrame"
            else:
                frame = "ItemSlotsFrame"
        if frame == "ItemSummaryFrame":
            self.ToggleItemView.setText("Item Slots")
            self.stackedlayout.setCurrentWidget(self.ItemSummaryFrame)
        else:
            self.ToggleItemView.setText("Item Info")
            self.stackedlayout.setCurrentWidget(self.ItemSlotsFrame)

    def insertSkill(self,amt,bonus,group):
        model = self.SkillsList.model()
        model.insertRows(model.rowCount(), 1)
        wid = 3
        if amt > -10 and amt < 10: wid += 1
        if bonus[0:4] == 'All ':
            bonus = "%*s%d %s)" % (wid - 1, "(", amt, bonus,)
        else:
            bonus = "%*d %s" % (wid, amt, bonus,)
        index = model.index(model.rowCount()-1, 0, QModelIndex())
        model.setData(index, QVariant(bonus), Qt.DisplayRole)
        model.setData(index, QVariant(group), Qt.UserRole)

    def summarize(self):
        charlevel = int(self.CharLevel.text())
        tot = {}
        tot['Cost'] = 0
        tot['Price'] = 0
        tot['Utility'] = 0.0
        tot['Stats'] = {}
        tot['Resists'] = {}
        tot['Skills'] = {}
        tot['Focus'] = {}
        tot['OtherBonuses'] = {}
        tot['PvEBonuses'] = {}
        for effect in DropLists['All']['Stat'] + ('AF', 'Fatigue', '% Power Pool'):
            tot['Stats'][effect] = {}
            tot['Stats'][effect]['TotalBonus'] = 0
            tot['Stats'][effect]['Bonus'] = 0
            tot['Stats'][effect]['TotalCapBonus'] = 0
            tot['Stats'][effect]['CapBonus'] = 0
            if HighCapBonusList.has_key(effect):
                capcalc = HighCapBonusList[effect]
                capcapcalc = HighCapBonusList[effect + ' Cap']
            else:
                capcalc = HighCapBonusList['Stat']
                capcapcalc = HighCapBonusList['Stat Cap']
            tot['Stats'][effect]['BaseCap'] \
                    = int(charlevel * capcalc[0]) + capcalc[1]
            tot['Stats'][effect]['BaseCapToCapBonus'] \
                    = int(charlevel * capcapcalc[0]) + capcapcalc[1]
        for effect in DropLists['All']['Resist']:
            tot['Resists'][effect] = {}
            tot['Resists'][effect]['TotalBonus'] = 0
            tot['Resists'][effect]['Bonus'] = 0
            race = str(self.CharRace.currentText())
            if Races['All'][race]['Resists'].has_key(effect):
                tot['Resists'][effect]['RacialBonus'] \
                        = Races['All'][race]['Resists'][effect]
            capcalc = HighCapBonusList['Resist']
            tot['Resists'][effect]['BaseCap'] \
                    = int(charlevel * capcalc[0]) + capcalc[1]
        for key, item in self.itemattrlist.iteritems():
            tot['Cost'] += item.cost()
            tot['Price'] += item.price(self.pricingInfo)
            if not item.Equipped == '1':
                continue
            tot['Utility'] += item.utility()
            for i in range(0, item.slotCount()):
                gemtype = item.slot(i).type()
                effect = item.slot(i).effect()
                amount = int('0'+re.sub('[^\d]', '', item.slot(i).amount()))
                if gemtype == 'Skill':
                    effects = [effect,]
                    if effect[0:4] == 'All ' and \
                       AllBonusList[self.realm][self.charclass].has_key(effect):
                        effects.extend(AllBonusList[self.realm] \
                                                   [self.charclass][effect])
                    for effect in effects:
                        if tot['Skills'].has_key(effect):
                            amts = tot['Skills'][effect]
                            amts['TotalBonus'] += amount
                        else:
                            tot['Skills'][effect] = {}
                            amts = tot['Skills'][effect]
                            amts['TotalBonus'] = amount
                            capcalc = HighCapBonusList['Skill']
                            amts['BaseCap'] = int(charlevel * capcalc[0]) \
                                            + capcalc[1]
                        amts['Bonus'] = min(amts['TotalBonus'], 
                                            amts['BaseCap'])
                elif gemtype == 'Focus':
                    effects = [effect,]
                    if effect[0:4] == 'All ':
                        effects.extend(AllBonusList[self.realm] \
                                                   [self.charclass][effect])
                    for effect in effects:
                        if effect == '': continue
                        if tot['Focus'].has_key(effect):
                            amts = tot['Focus'][effect]
                        else:
                            tot['Focus'][effect] = {}
                            amts = tot['Focus'][effect]
                            capcalc = HighCapBonusList['Focus']
                            amts['BaseCap'] = int(charlevel * capcalc[0]) \
                                            + capcalc[1]
                        amts['TotalBonus'] = amount
                        amts['Bonus'] = min(amts['TotalBonus'], 
                                            amts['BaseCap'])
                elif gemtype == 'Resist':
                    amts = tot['Resists'][effect]
                    amts['TotalBonus'] += amount
                    amts['Bonus'] = min(amts['TotalBonus'], 
                                        amts['BaseCap'])
                elif gemtype == 'Resist Cap' and item.TYPE == 'Mythirian':
                    amts = tot['Resists'][effect]
                    amts['BaseCap'] += amount
                    amts['Bonus'] = min(amts['TotalBonus'], 
                                        amts['BaseCap'])
                elif gemtype == 'Stat':
                    effects = [effect,]
                    if effect == 'Acuity':
                        effects.extend(AllBonusList[self.realm] \
                                                   [self.charclass][effect])
                    for effect in effects:
                        amts = tot['Stats'][effect]
                        amts['TotalBonus'] += amount
                        amts['Bonus'] = min(amts['TotalBonus'],
                                            amts['BaseCap'] + amts['CapBonus'])
                elif gemtype == 'Cap Increase':
                    effects = [effect,]
                    # Power cap affects both Power and % Power Pool
                    if effect == 'Power':
                        effects.append('% Power Pool')
                    elif effect == 'Acuity':
                        effects.extend(AllBonusList[self.realm] \
                                                   [self.charclass][effect])
                    for effect in effects:
                        amts = tot['Stats'][effect]
                        amts['TotalCapBonus'] += amount
                        if item.TYPE == 'Mythirian':
                            amts['BaseCapToCapBonus'] += amount
                        amts['CapBonus'] = min(amts['TotalCapBonus'],
                                               amts['BaseCapToCapBonus'])
                        amts['Bonus'] = min(amts['TotalBonus'],
                                            amts['BaseCap'] + amts['CapBonus'])
                elif gemtype == 'Other Bonus':
                    if effect in ('AF', 'Fatigue', '% Power Pool',):
                        amts = tot['Stats'][effect]
                        amts['TotalBonus'] += amount
                        amts['Bonus'] = min(amts['TotalBonus'],
                                            amts['BaseCap'] + amts['CapBonus'])
                        continue
                    if effect in ('Casting Speed', 'Archery Speed'):
                        effect = 'Archery and Casting Speed'
                    if effect in ('Spell Damage', 'Archery Damage'):
                        effect = 'Archery and Spell Damage'
                    if effect in ('Spell Range', 'Archery Range'):
                        effect = 'Archery and Spell Range'
                    if not tot['OtherBonuses'].has_key(effect):
                        tot['OtherBonuses'][effect] = {}
                        amts = tot['OtherBonuses'][effect]
                        amts['TotalBonus'] = amount
                        if HighCapBonusList.has_key(effect):
                            capcalc = HighCapBonusList[effect]
                        else:
                            capcalc = HighCapBonusList[gemtype]
                        amts['BaseCap'] = int(charlevel * capcalc[0]) \
                                        + capcalc[1]
                    else:
                        amts = tot['OtherBonuses'][effect]
                        amts['TotalBonus'] += amount
                    if item.TYPE == 'Mythirian':
                        amts['BaseCap'] += amount
                    amts['Bonus'] = min(amts['TotalBonus'], 
                                        amts['BaseCap'])
                elif gemtype == 'PvE Bonus':
                    if tot['PvEBonuses'].has_key(effect):
                        amts = tot['PvEBonuses'][effect]
                        amts['TotalBonus'] += amount
                    else:
                        tot['PvEBonuses'][effect] = {}
                        amts = tot['PvEBonuses'][effect]
                        if HighCapBonusList.has_key(effect):
                            capcalc = HighCapBonusList[effect]
                        else:
                            capcalc = HighCapBonusList[gemtype]
                        amts['BaseCap'] = int(charlevel * capcalc[0]) \
                                        + capcalc[1]
                        amts['TotalBonus'] = amount
                    amts['Bonus'] = min(amts['TotalBonus'], amts['BaseCap'])
        tot['Price'] += self.pricingInfo.get('PPOrder', 0) * 10000
        if self.pricingInfo.get('HourInclude', 0) \
                   and self.CraftTime.text() > '':
            tot['Price'] += int(self.pricingInfo.get('Hour', 0) * 10000 \
                           * int(self.CraftTime.text()) / 60.0)
        return tot

    def showStat(self, stat, show):
        if self.StatLabel[stat].isHidden() != show:
            return
        self.StatLabel[stat].setVisible(show)
        self.StatValue[stat].setVisible(show)
        self.StatCap[stat].setVisible(show)

    def calculate(self):
        if self.nocalc:
            return
        errorcount = 0
        enableCrafting = False
        self.errorsmenu.clear()
        charleveltext = str(self.CharLevel.text())
        if charleveltext == '': 
            charlevel = 1
        else:
            charlevel = max(min(50, int(charleveltext)), 1)
        self.CharLevel.setText(str(charlevel))
        for key, item in self.itemattrlist.iteritems():
            if item.ActiveState != 'player': continue
            gemeffects = []
            for i in range(0, item.slotCount()):
                slot = item.slot(i)
                if slot.slotType() != 'player': continue
                gemtype = slot.type()
                if gemtype == 'Unused': continue
                effect = slot.effect()
                if [gemtype, effect] in gemeffects:
                    error_act = QAction('Two of same type of gem on %s' \
                                        % key, self)
                    if item.Location in JewelTabList:
                        row = 1
                        col = JewelTabList.index(item.Location)
                    else:
                        row = 0
                        col = PieceTabList.index(item.Location)
                    error_act.setData(QVariant((row << 8) | col))
                    self.errorsmenu.addAction(error_act)
                    errorcount = errorcount + 1
                gemeffects.append([gemtype, effect])
        item = self.itemattrlist[self.currentTabLabel]
        self.ItemUtility.setText('%3.1f' % item.utility())
        if item.ActiveState == 'player':
            imbuevals = item.listGemImbue()
            imbuepts = sum(imbuevals)
            itemimbue = item.itemImbue()
            for i in range(0, item.slotCount()):
                slot = item.slot(i)
                if i < len(imbuevals):
                    self.Cost[i].setText(SC.formatCost(slot.gemCost(1)))
                    self.Points[i].setText('%3.1f' % imbuevals[i])
                    if slot.crafted():
                        enableCrafting = True
                self.Name[i].setText(slot.gemName(self.realm))
                self.Name[i].setToolTip(slot.gemName(self.realm))
            self.ItemImbue.setText('%3.1f' % imbuepts)
            self.ItemImbueTotal.setText(' / ' + unicode(itemimbue))
            self.ItemCost.setText(SC.formatCost(item.cost()))
            self.ItemPrice.setText(SC.formatCost(item.price(self.pricingInfo)))
            if imbuepts >= (itemimbue + 6.0):
                self.ItemOvercharge.setText('Impossible')
                error_act = QAction('Impossible overcharge on %s' % key, self)
                if item.Location in JewelTabList:
                    row = 1
                    col = JewelTabList.index(item.Location)
                else:
                    row = 0
                    col = PieceTabList.index(item.Location)
                error_act.setData(QVariant((row << 8) | col))
                self.errorsmenu.addAction(error_act)
                errorcount = errorcount + 1
            elif imbuepts < (itemimbue + 1.0):
                self.ItemOvercharge.setText('None')
            else:
                success = item.overchargeSuccess(self.crafterSkill)
                if success < 0:
                    self.ItemOvercharge.setText('BOOM! (%d%%)' % success)
                else:
                    self.ItemOvercharge.setText('%d%%' % success)
        tot = self.summarize()
        self.SkillsList.model().removeRows(0,self.SkillsList.model().rowCount())
        for key, amounts in tot['Resists'].iteritems():
            val = amounts['TotalBonus']
            if not self.capDistance:
                if self.includeRacials:
                    if amounts.has_key('RacialBonus'):
                        rr = amounts['RacialBonus']
                        val += rr
                self.StatValue[key].setText(unicode(val))
            else:
                basecap = amounts['BaseCap']
                self.StatValue[key].setText(unicode(basecap - val))
        for (key, datum) in tot['Stats'].iteritems():
            val = datum['TotalBonus']
            acuity = AllBonusList[self.realm][self.charclass]["Acuity"]
            if key == "% Power Pool":
                key = "PowerPool"
            if key[:5] == "Power":
                skills = AllBonusList[self.realm][self.charclass]["All Magic Skills"]
                self.showStat(key, (datum['TotalCapBonus'] > 0) \
                                 or (val > 0) or (len(skills) > 0))
            elif key == "Fatigue":
                skills = AllBonusList[self.realm][self.charclass]["All Melee Weapon Skills"]
                self.showStat(key, (datum['TotalCapBonus'] > 0) \
                                 or (val > 0) or (len(skills) > 0))
            elif key == "Acuity":
                self.showStat(key, ((datum['TotalCapBonus'] > 0) \
                                 or (val > 0)) and (len(acuity) == 0))
            elif key in ("Charisma", "Empathy", "Intelligence", "Piety"):
                self.showStat(key, (datum['TotalCapBonus'] > 0) \
                                or (val > 0) or (key in acuity))
            if not self.capDistance:
                if datum['TotalCapBonus'] > 0:
                    self.StatCap[key].setText( \
                        '('+str(datum['TotalCapBonus'])+')')
                else:
                    self.StatCap[key].setText('-')
                self.StatValue[key].setText(unicode(val))
            else:
                basecap = datum['BaseCap']
                addcap = datum['BaseCapToCapBonus']
                if datum['TotalCapBonus'] > 0:
                    capmod = datum['TotalCapBonus']
                else:
                    capmod = 0
                capcap = addcap - capmod
                if capmod > addcap:  capmod = addcap
                self.StatCap[key].setText('('+unicode(int(capcap))+')')
                self.StatValue[key].setText(unicode(int(basecap + capmod) -val))
        for skillkey, suffix, lookup in (
                ('Skills', '', 'Skill'),
                ('Focus', ' Focus', 'Focus'),
                ('OtherBonuses', '', 'Bonus'),
                ('PvEBonuses', ' (PvE)', 'Bonus')):
            skills = tot[skillkey].keys()
            skills.sort()
            for skill in skills:
                amounts = tot[skillkey][skill]
                if self.capDistance:
                    amount = amounts['BaseCap'] - amounts['TotalBonus']
                else:
                    amount = amounts['TotalBonus']
                self.insertSkill(amount, skill + suffix, lookup)
        self.TotalCost.setText(SC.formatCost(tot['Cost']))
        self.TotalPrice.setText(SC.formatCost(tot['Price']))
        self.TotalUtility.setText('%3.1f' % tot['Utility'])
        self.errorsmenuid.setEnabled(errorcount > 0)
        item = self.itemattrlist[self.currentTabLabel]
        self.craftingmenuid.setEnabled(enableCrafting)
        self.craftingtoolid.setEnabled(enableCrafting)
                
    def templateChanged(self,a0=None):
        self.modified = True

    def totalsChanged(self,a0=None):
        if self.nocalc: return
        self.modified = True
        self.calculate()

    def raceChanged(self, a0):
        race = str(self.CharRace.currentText())
        for rt in DropLists['All']['Resist']:
            if Races['All'][race]['Resists'].has_key(rt):
              if self.includeRacials:
                self.StatBonus[rt].setText('('+str(Races['All'][race] \
                                                        ['Resists'][rt])+')')
              else:
                self.StatBonus[rt].setText('+'+str(Races['All'][race] \
                                                        ['Resists'][rt]))
            else:
                self.StatBonus[rt].setText('-')
        if self.nocalc: return
        self.modified = True
        self.restoreItem(self.itemattrlist[self.currentTabLabel])

    def charClassChanged(self,a0):
        self.charclass = str(self.CharClass.currentText())
        showrealm = self.realm
        if self.coop:
            showrealm = 'All'
        self.dropeffectlists['Skill'] = DropLists[showrealm]['Skill']
        self.dropeffectlists['Focus'] = DropLists[showrealm]['Focus']
        if self.hideNonClassSkills:
            self.effectlists['Skill'] = AllBonusList['All'][self.charclass] \
                                                    ['All Skills']
            self.effectlists['Focus'] = AllBonusList['All'][self.charclass] \
                                                    ['All Focus']
        else:
            self.effectlists['Skill'] = GemLists[showrealm]['Skill']
            self.effectlists['Focus'] = GemLists[showrealm]['Focus']
        race = str(self.CharRace.currentText())
        self.CharRace.clear()
        racelist = AllBonusList[self.realm][self.charclass]['Races']
        self.CharRace.insertItems(0, list(racelist))
        if race not in racelist:
            race = racelist[0]
        self.CharRace.setCurrentIndex(racelist.index(race))
        self.raceChanged(racelist.index(race))
        self.restoreItem(self.itemattrlist[self.currentTabLabel])

    def realmChanged(self,a0):
        self.realm = str(self.Realm.currentText())
        self.CharClass.clear()
        self.CharClass.insertItems(0, list(ClassList[self.realm]))
        if self.charclass not in ClassList[self.realm]:
            self.charclass = ClassList[self.realm][0]
        self.CharClass.setCurrentIndex(
                           ClassList[self.realm].index(self.charclass))
        self.charClassChanged(self.CharClass.currentIndex())

    def itemLevelShow(self):
        level = self.ItemLevelWindow.exec_()
        if level != -1:
            self.ItemLevel.setText(str(level))
            self.AFDPSEdit.setText(str(self.ItemLevelWindow.afdps))
        self.itemInfoChanged()

    def displayClassRestrictions(self, item):
        classitem = self.ClassRestrictionTable.item(0)
        if len(item.CLASSRESTRICTIONS) > 0 and \
               item.CLASSRESTRICTIONS[0] == 'All':
            classitem.setCheckState(Qt.Checked)
            cr = 1
        else:
            classitem.setCheckState(Qt.Unchecked)
            cr = 0
        classlist = ClassList[item.Realm]
        # This reset() prepares the X11 port to correctly position
        # the soon-to-be visible class names
        self.ClassRestrictionTable.reset()
        rc = 0
        i = 1
        for classname in ClassList['All']:
            classitem = self.ClassRestrictionTable.item(i)
            if rc < len(classlist) and classlist[rc] == classname:
                self.ClassRestrictionTable.item(i).setHidden(False)
                if cr < len(item.CLASSRESTRICTIONS) and \
                   item.CLASSRESTRICTIONS[cr] == classname:
                    classitem.setCheckState(Qt.Checked)
                    cr = cr + 1
                else:
                    classitem.setCheckState(Qt.Unchecked)
                rc = rc + 1
            else:
                self.ClassRestrictionTable.item(i).setHidden(True)
                classitem.setCheckState(Qt.Unchecked)
                if cr < len(item.CLASSRESTRICTIONS) and \
                   item.CLASSRESTRICTIONS[cr] == classname:
                    del self.CLASSRESTRICTIONS[cr]
            i = i + 1

    def classRestrictionsChanged(self,a0=None):
        item = self.itemattrlist[self.currentTabLabel]
        if self.nocalc: return
        if a0.text() == "All":
            if a0.checkState() == Qt.Checked:
                for row in range(1, self.ClassRestrictionTable.count()):
                   self.ClassRestrictionTable.item(row).setCheckState(Qt.Unchecked)
                item.CLASSRESTRICTIONS = ['All']
            elif 'All' in item.CLASSRESTRICTIONS:
                index = item.CLASSRESTRICTIONS.index('All')
                del item.CLASSRESTRICTIONS[index]
            else:
                return
        elif a0.checkState() == Qt.Checked:
            if self.ClassRestrictionTable.item(0).checkState() == Qt.Checked:
                self.ClassRestrictionTable.item(0).setCheckState(Qt.Unchecked)
            if 'All' in item.CLASSRESTRICTIONS:
                index = item.CLASSRESTRICTIONS.index('All')
                del item.CLASSRESTRICTIONS[index]
            i = 0
            while i < len(item.CLASSRESTRICTIONS):
                if a0.text() == item.CLASSRESTRICTIONS[i]:
                    return
                if a0.text() > item.CLASSRESTRICTIONS[i]:
                    break
                i = i + 1
            item.CLASSRESTRICTIONS.insert(i, str(a0.text()))
        elif a0.text() in item.CLASSRESTRICTIONS:
            index = item.CLASSRESTRICTIONS.index(str(a0.text()))
            del item.CLASSRESTRICTIONS[index]
        else:
            return
        self.modified = True

    def itemInfoChanged(self,a0=None):
        if self.nocalc: return
        self.modified = True
        item = self.itemattrlist[self.currentTabLabel]
        item.SOURCE = unicode(self.ItemSource.currentText())
        item.Bonus = unicode(self.BonusEdit.text())
        item.Requirement = unicode(self.ItemRequirement.text())
        item.AFDPS = unicode(self.AFDPSEdit.text())
        item.Speed = unicode(self.SpeedEdit.text())
        item.DAMAGETYPE = unicode(self.DamageType.currentText())
	if self.Offhand.checkState() == Qt.Checked:
            item.OFFHAND = 'yes'
        elif self.Offhand.isVisible() or len(item.OFFHAND) > 0:
            item.OFFHAND = 'no' 

    def itemNotesChanged(self,a0=None):
        if self.nocalc: return
        self.modified = True
        item.Notes = unicode(self.ItemNoteText.toPlainText())

    def itemChanged(self,a0=None):
        if self.nocalc: return
        self.modified = True
        item = self.itemattrlist[self.currentTabLabel]
        self.fixupItemLevel()
        item.Level = unicode(self.ItemLevel.text())
        if self.Equipped.isChecked():
            item.Equipped = '1'
        else:
            item.Equipped = '0'
        self.outfitlist[self.currentOutfit][self.currentTabLabel] \
                = ( item.TemplateIndex, item.Equipped, )
        if item.ActiveState == 'player':
            item.ItemQuality = unicode(self.QualDrop.currentText())
            item.Time = unicode(self.ItemCraftTime.text())
            if item.Time == '': item.Time = u'0'
        else:
            item.ItemQuality = unicode(self.QualEdit.text())
        self.calculate()

    def event(self, e):
        if e.type() == UserEventItemNameUpdatedID:
            self.ItemNameCombo.setCurrentIndex(0)
            return True
        else:
            return QMainWindow.event(self, e)

    def itemNameSelected(self,a0):
        # only items other-than-current are interesting to us
        if self.nocalc or not isinstance(a0, int) or (a0 < 1):
            return
        #sys.stdout.write("Selected Item %s\n" % str(a0))
        item = self.itemattrlist[self.currentTabLabel]
        wasequipped = item.Equipped
        item.Equipped = '0'
        prev = item
        for a1 in range(0, a0 - 1):
            prev = prev.next
        item = prev.next
        prev.next = prev.next.next
        item.next = self.itemattrlist[self.currentTabLabel]
        self.itemattrlist[self.currentTabLabel] = item
        item.Equipped = wasequipped
        self.outfitlist[self.currentOutfit][self.currentTabLabel] \
                = ( item.TemplateIndex, item.Equipped, )
        self.nocalc = True
        self.restoreItem(item)
        self.nocalc = False
        self.calculate()
        # The currentIndex is correct; however the value in the edit 
        # text is not.  Re-Select item after this event is processed
        QApplication.postEvent(self, UserEventItemNameUpdated())

    def itemNameEdited(self,a0):
        # Ignore side-effect signal textEditChanged() prior to activated()
        if self.nocalc or (self.ItemNameCombo.currentIndex() != 0):
            return
        # Don't update as we stumble upon a duplicate name, 
        # or we see an edit message for a newly selected item.
        # let them keep editing or proceed to update the combo
        if self.ItemNameCombo.findText(a0) > -1:
            return
        #sys.stdout.write("Edited Item %d named %s\n" % (self.ItemNameCombo.currentIndex(), a0))
        item = self.itemattrlist[self.currentTabLabel]
        item.ItemName = unicode(self.ItemNameCombo.lineEdit().text())
        cursorpos = self.ItemNameCombo.lineEdit().cursorPosition()
        self.ItemNameCombo.setItemText(0,item.ItemName)
        self.ItemNameCombo.lineEdit().setCursorPosition(cursorpos)
        self.modified = True

    def senderSlot(self):
        index = self.sender().objectName()[-2:]
        if index[0] == '_': index = index[1:]
        return int(index) - 1

    def amountsChanged(self, amount = None, slot = -1):
        if self.nocalc: return
        if slot < 0:
            slot = self.senderSlot()      
        item = self.itemattrlist[self.currentTabLabel]
        if item.ActiveState == 'player':
            item.slot(slot).setAmount(self.AmountDrop[slot].currentText())
            if item.slot(slot).slotType() == 'effect':
                amount = self.AmountDrop[slot].currentIndex()
                typetext = item.slot(slot).type()
                efftext = item.slot(slot).effect()
                if (ValuesLists.has_key(typetext)
                and isinstance(ValuesLists[typetext], dict)):
                    valueslist = ValuesLists[typetext]
                    if (valueslist.has_key(efftext)
                    and isinstance(valueslist[efftext][0], tuple)
                    and len(valueslist[efftext][1]) > amount):
                        # On change-tincture amounts, fix requirement
                        valueslist = valueslist[efftext]
                        req = "Level %s" % valueslist[1][amount]
                        self.Requirement[slot].setText(req)
        else:
            item.slot(slot).setAmount(self.AmountEdit[slot].text())
        if item.slot(slot).slotType() == 'player':
            item.slot(slot).setMakes(str(self.Makes[slot].value()))
        else:
            item.slot(slot).setRequirement(self.Requirement[slot].text())
        self.modified = True
        self.calculate()

    def effectChanged(self, value = None, slot = -1):
        if slot < 0:
            slot = self.senderSlot()        
        item = self.itemattrlist[self.currentTabLabel]
        if isinstance(value,int):
            efftext = str(self.Effect[slot].currentText())
        else:
            efftext = str(self.Effect[slot].lineEdit().text())
        if not self.nocalc:
            item.slot(slot).setEffect(efftext)
            self.modified = True
        typetext = str(item.slot(slot).type())
        effcombo = self.Effect[slot]
        unique = ((len(efftext) > 3 and efftext[-3:] == "...") \
               or not isinstance(value,int))
        if effcombo.isEditable() and not unique:
            refocus = self.Effect[slot].hasFocus()
            effcombo.setEditable(False)
            self.fix_taborder(slot)
        elif unique and not effcombo.isEditable():
            refocus = self.Effect[slot].hasFocus()
            effcombo.setEditable(True)
            self.fix_taborder(slot)
            if refocus:
                effcombo.lineEdit().selectAll()
        else:
            refocus = False
        if refocus:
            flip = self.Effect[slot].setFocus()
        if item.ActiveState == 'player':
            amount = self.AmountDrop[slot]
        else:
            amount = self.AmountEdit[slot]
        if typetext == 'Unused':
            amount.clear()
            if item.slot(slot).slotType() == 'player':
                self.Makes[slot].setValue(0)
                self.Makes[slot].setMaximum(0)
            else:
                self.Requirement[slot].setText("")
        elif item.ActiveState == 'player':
            amtindex = amount.currentIndex()
            amount.clear()
            if item.slot(slot).slotType() == 'crafted':
                valueslist = CraftedValuesLists
            else:
                valueslist = ValuesLists
            if valueslist.has_key(typetext):
                valueslist = valueslist[typetext]
                if isinstance(valueslist, dict):
                    if valueslist.has_key(efftext):
                        valueslist = valueslist[efftext]
                        if isinstance(valueslist[0], tuple):
                            if (len(valueslist[0]) > 1 and amtindex < 1
                            and (valueslist[2] == 0 or valueslist[2] == 8)):
                                # Let's default to crafted tincts
                                amtindex = 1
                            valueslist = valueslist[0]
                    elif valueslist.has_key(None):
                        valueslist = valueslist[None]
                    else:
                        valueslist = tuple()
                elif efftext[0:5] == "All M":
                    valueslist = valueslist[:1]
                if len(valueslist) > 0:
                    amount.insertItems(0, list(valueslist))
                if amtindex < 0:
                    amtindex = 0
                if amtindex < len(valueslist):
                    amount.setCurrentIndex(amtindex)
            if item.slot(slot).slotType() == 'player':
                self.Makes[slot].setMaximum(99)
        # Cascade the changes
        self.amountsChanged(None, slot)

    def typeChanged(self, Value = None, slot = -1):
        if slot < 0:
            slot = self.senderSlot()
        item = self.itemattrlist[self.currentTabLabel]
        typetext = str(self.Type[slot].currentText())
        if not self.nocalc:
            item.slot(slot).setType(typetext)
            self.modified = True

        effcombo = self.Effect[slot]
        if effcombo.isEditable():
            effcombo.setEditable(False)
            self.fix_taborder(slot)
        effcombo.clear()

        if item.ActiveState == 'player':
            if item.slot(slot).slotType() == 'crafted':
                effectlist = self.itemeffectlists
            else:
                effectlist = self.effectlists
        else:
            effectlist = self.dropeffectlists
        if effectlist.has_key(typetext):
            effectlist = effectlist[typetext]
        else:
            effectlist = list()
        if len(effectlist) > 0:
            effcombo.insertItems(0, list(effectlist))
        i = 0
        if typetext == 'Skill':
            while (i < len(effectlist) and effectlist[i][:5] == 'All M'):
                i = i + 1
        effcombo.setCurrentIndex(i)
        # Here we go... cascade
        self.effectChanged(i, slot)
    
    def clearCurrentItemSlots(self):
        self.itemattrlist[self.currentTabLabel].clearSlots()
        if self.nocalc: return
        self.modified = True
        self.restoreItem(self.itemattrlist[self.currentTabLabel])

    def clearCurrentItem(self):
        item = self.itemattrlist[self.currentTabLabel]
        item = Item(realm=self.realm,loc=self.currentTabLabel,
                    state=item.ActiveState,
                    idx=item.TemplateIndex)
        if item.ActiveState == 'drop':
            item.ItemName = "Drop Item" + str(self.itemnumbering)
        else:
            item.ItemName = "Crafted Item" + str(self.itemnumbering)
        self.itemattrlist[self.currentTabLabel] = item
        self.itemnumbering += 1
        if self.nocalc: return
        self.modified = True
        self.restoreItem(self.itemattrlist[self.currentTabLabel])

    def deleteCurrentItem(self):
        if self.itemattrlist[self.currentTabLabel].next is None:
            self.clearCurrentItem()
            return
        item = self.itemattrlist[self.currentTabLabel]
        self.itemattrlist[self.currentTabLabel] = item.next
        item.next = None
        if item.Equipped == '1':
            self.itemattrlist[self.currentTabLabel].Equipped = '1'
        for outfit in self.outfitlist:
             outfititem = outfit[self.currentTabLabel]
             if outfititem[0] == item.TemplateIndex:
                 outfit[self.currentTabLabel] = (
                     self.itemattrlist[self.currentTabLabel].TemplateIndex,
                     self.itemattrlist[self.currentTabLabel].Equipped,)
        if self.nocalc: return
        self.modified = True
        self.restoreItem(self.itemattrlist[self.currentTabLabel])

    def chooseItemPath(self):
        itemdir = QFileDialog.getExistingDirectory(self, 
                      'Select Item Database Path', self.ItemPath)
        if itemdir:
            self.ItemPath = os.path.abspath(unicode(itemdir))
            ret = QMessageBox.question(self, 'Create Database Directories?', 
                                       "Create realm and item slot directories"\
                                     + " underneath %s ?" % itemdir, 
                                       QMessageBox.Yes, QMessageBox.No)
            if ret == QMessageBox.Yes:
                realms = list(Realms)
                realms.append("All")
                for realm in realms:
                    itempath = os.path.join(self.ItemPath, realm)
                    if not os.path.exists(itempath):
                        os.makedirs(itempath)
                    for ext in FileExt.values():
                        if ext == '*':
                            continue
                        if not isinstance(ext, types.StringType):
                            ext = ext[0]
                        itempath = os.path.join(self.ItemPath, realm, ext)
                        if not os.path.exists(itempath):
                            os.makedirs(itempath)

    def saveItem(self):
        itemname = string.replace(unicode(self.ItemNameCombo.currentText()),
                                  ' ', '_')
        if itemname == '':
            QMessageBox.critical(self, 'Error!', 
                'Cannot save item - You must specify a name!', 'OK')
            return
        item = self.itemattrlist[self.currentTabLabel]

        item.Realm = self.realm

        ext = FileExt[self.currentTabLabel]
        extstr = ''
        if not isinstance(ext, types.StringType):
            for e in ext:
                extstr += '*%s.xml ' % e
            ext = ext[0]
        else:
            extstr = '*%s.xml' % ext
        extstr = "Items (%s);;All Files (*.*)" % extstr.rstrip()
        itemname = itemname + '_' + ext + '.xml'
        itemdir = self.ItemPath
        recentdir = []
        if os.path.exists(os.path.join(itemdir, self.realm, ext)):
            itemdir = os.path.join(self.ItemPath, self.realm, ext)
            if self.coop:
                for realm in Realms:
                    if realm != self.realm:
                        recentdir.append(os.path.join(self.ItemPath, realm,ext))
            recentdir.append(os.path.join(self.ItemPath, "All", ext))
        filename = os.path.join(itemdir, itemname)
        filename = QFileDialog.getSaveFileName(self, "Save Item", filename, 
                                   "Templates (*.xml);;All Files (*.*)")
        filename = unicode(filename)
        if filename != '':
            item.save(filename)

    def loadItem(self):
        ext = FileExt[self.currentTabLabel]
        extstr = ''
        if not isinstance(ext, types.StringType):
            for e in ext:
                extstr += '*%s.xml *.%s ' % (e, e)
            ext = ext[0]
        else:
            extstr = '*%s.xml *.%s' % (ext, ext)
        extstr = "Items (%s);;All Files (*.*)" % extstr.rstrip()
        itemdir = self.ItemPath
        recentdir = []
        if os.path.exists(os.path.join(itemdir, self.realm, ext)):
            itemdir = os.path.join(self.ItemPath, self.realm, ext)
            if self.coop:
                for realm in Realms:
                    if realm != self.realm:
                        recentdir.append(os.path.join(self.ItemPath, realm,ext))
            recentdir.append(os.path.join(self.ItemPath, "All", ext))
        elif os.path.exists(os.path.join(itemdir, 'All', ext)):
            itemdir = os.path.join(self.ItemPath, 'All', ext)
        Qfd = ItemList.ItemListDialog(self, "Load Item", itemdir, extstr, 
                                      self.realm, self.charclass)
        Qfd.setHistory(recentdir)
        if Qfd.exec_():
            if Qfd.selectedFiles().count() > 0:
                filename = unicode(Qfd.selectedFiles()[0])
                item = Item('drop', self.currentTabLabel, self.realm,
                    self.itemIndex)
                if item.load(filename,str(self.itemnumbering)) == -1: return
                if string.lower(item.Realm) != string.lower(self.realm)\
                    and string.lower(item.Realm) != 'all'\
                    and not self.coop:
                    QMessageBox.critical(None, 'Error!',
                                         'You are trying to load an ' \
                                       + 'item for another realm!', 'OK')
                    return
                self.itemIndex += 1
                self.itemnumbering += 1
                if item.next:
                    item.next.TemplateIndex = self.itemIndex
                    self.itemIndex += 1
                item.Location = self.currentTabLabel
                item.Equipped = self.itemattrlist[self.currentTabLabel].Equipped
                self.itemattrlist[self.currentTabLabel].Equipped = '0'
                item.next = self.itemattrlist[self.currentTabLabel]
                self.itemattrlist[self.currentTabLabel] = item
                self.outfitlist[self.currentOutfit][self.currentTabLabel] \
                          = ( item.TemplateIndex, item.Equipped, )
                self.restoreItem(item)
                self.modified = True

    def newFile(self):
        if self.modified:
            ret = QMessageBox.warning(self, 'Save Changes?', 
                                      "This template has been changed.\n"
                                      "Do you want to save these changes?", 
                                      QMessageBox.Yes, QMessageBox.No,
                                      QMessageBox.Cancel)
            if ret == QMessageBox.Cancel: return
            if ret == QMessageBox.Yes:
                self.saveFile()
                if self.modified: return
        self.initialize(False)

    def saveFile(self):
        if self.filename is None:
            self.saveAsFile()
        else:
            try:
                xmlbody = self.asXML()
            except Exception, ex:
                print 'Error converting template to XML: ', ex
                QMessageBox.critical(None, 'Error!', 
                    "Error creating xml to save this template\r\n\r\n" \
                  + "Please share your Spellcraft.exe.log error report with " \
                  + "http://sourceforge.net/projects/kscraft", 'OK')
                return
            try:
                f = open(self.filename, 'w')
                f.write(XMLHelper.writexml(xmlbody, UnicodeStringIO(),
                                           '', '\t', '\n'))
                f.close()
                self.modified = False
            except IOError:
                QMessageBox.critical(None, 'Error!', 
                    'Error writing to file: ' + self.filename, 'OK')

    def saveAsFile(self):
        filename = self.filename
        if filename is None:
            filename = os.path.join(self.TemplatePath,
                                    str(self.CharName.text()) + "_template.xml")
        filename = unicode(filename)
        filename = QFileDialog.getSaveFileName(self, "Save Template", filename, 
                                   "Templates (*.xml);;All Files (*.*)")
        filename = unicode(filename)
        if filename != '':
            if filename[-4:] != '.xml':
                filename += '.xml'
            try:
                xmlbody = self.asXML()
            except Exception, ex:
                print 'Error converting template to XML: ', ex
                QMessageBox.critical(None, 'Error!', 
                    "Error creating xml to save this template\r\n\r\n" \
                  + "Please share your Spellcraft.exe.log error report with " \
                  + "http://sourceforge.net/projects/kscraft", 'OK')
                return
            try:
                f = open(filename, 'w')
                f.write(XMLHelper.writexml(xmlbody, UnicodeStringIO(),
                                           '', '\t', '\n'))
                f.close()
            except IOError:
                QMessageBox.critical(None, 'Error!', 
                    'Error writing to file: ' + filename, 'OK')
                return
            self.modified = False
            self.filename = os.path.abspath(filename)
            self.updateRecentFiles(self.filename)
            self.TemplatePath = os.path.dirname(self.filename)
            filetitle = os.path.basename(self.filename)
            self.setWindowTitle(filetitle +" - Kort's Spellcrafting Calculator")
            
    def exportAsFile(self):
        filename = os.path.join(self.ReportPath, str(self.CharName.text()) \
                                               + "_report.xml")
        filename = unicode(filename)
        filename = QFileDialog.getSaveFileName(self, "Save SCTemplate XML", 
                       filename, "SCTemplates (*_report.xml);;All Files (*.*)")
        filename = unicode(filename)
        if filename != '':
            if filename[-4:] != '.xml':
                filename += '.xml'
            try:
                xmlbody = self.asXML(True)
            except Exception, ex:
                print 'Error converting template to XML: ', ex
                QMessageBox.critical(None, 'Error!', 
                    "Error creating xml to export this template\r\n\r\n" \
                  + "Please share your Spellcraft.exe.log error report with " \
                  + "http://sourceforge.net/projects/kscraft", 'OK')
                return
            try:
                f = open(filename, 'w')
                f.write(XMLHelper.writexml(xmlbody, UnicodeStringIO(),
                                           '', '\t', '\n'))
                f.close()
            except IOError:
                QMessageBox.critical(None, 'Error!', 
                    'Error writing to file: ' + filename, 'OK')
                return
            self.ReportPath = os.path.dirname(os.path.abspath(filename))
            
    def openFile(self, *args):
        if self.modified:
            ret = QMessageBox.warning(self, 'Save Changes?', 
                                      "This template has been changed.\n"
                                      "Do you want to save these changes?", 
                                      QMessageBox.Yes, QMessageBox.No,
                                      QMessageBox.Cancel)
            if ret == QMessageBox.Cancel: return
            if ret == QMessageBox.Yes:
                self.saveFile()
                if self.modified: return
        if len(args) == 0:
            filename = QFileDialog.getOpenFileName(self, "Open Template",
                            self.TemplatePath, 
                            "Templates (*.xml);;All Files (*.*)")
        else:
            filename = args[0]
        filename = unicode(filename)
        if filename is not None and filename != '':
            f = None
            try:
                f = open(filename, 'r')
                docstr = f.read()
            except:
                QMessageBox.critical(None, 'Error!', 
                    'Error reading template file ' + unicode(filename), 'OK')
                if f is not None: f.close()
                return
            try:
                f = open(filename, 'r')
                docstr = f.read()
                if docstr[0:5] == '<?xml':
                    xmldoc = parseString(docstr)
                    template = xmldoc.getElementsByTagName('SCTemplate')
                    self.loadFromXML(template[0])
                else:
                    QMessageBox.critical(None, 'Error!', 
                        'Unrecognized Template Type', 'OK')
                    f.close()
                    return
            except Exception, ex:
                print 'Error loading template file: ', ex
                QMessageBox.critical(None, 'Error!', \
                    "Error loading template file " + unicode(filename) \
                  + "\r\n(Perhaps this isn't a spellcrafting template file?)" \
                  + "\r\n\r\nPlease share this template file and your " \
                  + "Spellcraft.exe.log error report with the authors at " \
                  + "http://sourceforge.net/projects/kscraft", 'OK')
                if f is not None: f.close()
                return
            self.filename = os.path.abspath(filename)
            self.updateRecentFiles(self.filename)
            self.TemplatePath = os.path.dirname(self.filename)
            filetitle = os.path.basename(self.filename)
            self.setWindowTitle(filetitle +" - Kort's Spellcrafting Calculator")

    def updateRecentFiles(self, fn):
        if fn is not None:
            while fn in self.recentFiles:
                self.recentFiles.remove(fn)
            self.recentFiles.insert(0, fn)
        if len(self.recentFiles) > 5:
            del self.recentFiles[5:]
        self.rf_menu.clear()
        for count in range(0, len(self.recentFiles)):
            act = QAction('&%d %s' % (count + 1, self.recentFiles[count]), self)
            act.setData(QVariant(count))
            self.rf_menu.addAction(act)

    def loadFromXML(self, template):
        self.initialize(True)
        self.OutfitName.clear()
        racename = ''
        classname = ''
        self.outfitlist = []
        self.outfitnumbering = 1
        self.currentOutfit = 0
        self.itemnumbering = 1
        itemdefault = self.itemattrlist.copy()
        for child in template.childNodes:
            if child.nodeType == Node.TEXT_NODE: continue
            if child.tagName == 'Name':
                self.CharName.setText(XMLHelper.getText(child.childNodes))
            elif child.tagName == 'Class':
                self.charclass = XMLHelper.getText(child.childNodes)
            elif child.tagName == 'Race':
                racename = XMLHelper.getText(child.childNodes)
            elif child.tagName == 'Realm':
                self.realm = XMLHelper.getText(child.childNodes)
            elif child.tagName == 'Level':
                self.CharLevel.setText(XMLHelper.getText(child.childNodes))
            elif child.tagName == 'RealmRank':
                self.RealmRank.setText(XMLHelper.getText(child.childNodes))
            elif child.tagName == 'ChampionLevel':
                self.ChampionLevel.setText(XMLHelper.getText(child.childNodes))
            elif child.tagName == 'CraftTime':
                self.CraftTime.setText(XMLHelper.getText(child.childNodes))
            elif child.tagName == 'Notes':
                self.NoteText.setPlainText(XMLHelper.getText(child.childNodes))
            elif child.tagName == 'SCItem':
                newItem = Item(realm=self.realm)
                newItem.loadFromXML(child,str(self.itemnumbering),True)
                if newItem.TemplateIndex == -1:
                    newItem.TemplateIndex = self.itemIndex
                    self.itemIndex += 1
                else:
                    self.itemIndex = max(newItem.TemplateIndex + 1, self.itemIndex)
                if newItem.next:
                    if newItem.next.TemplateIndex == -1:
                        newItem.next.TemplateIndex = self.itemIndex
                        self.itemIndex += 1
                    else:
                        self.itemIndex = max(newItem.next.TemplateIndex + 1, self.itemIndex)

                self.itemnumbering += 1
                if self.itemattrlist[newItem.Location] \
                      == itemdefault[newItem.Location]:
                    self.itemattrlist[newItem.Location] = newItem
                elif newItem.Equipped == '1':
                    self.itemattrlist[newItem.Location].Equipped = '0'
                    item = newItem
                    while item.next is not None:
                        item = item.next
                    item.next = self.itemattrlist[newItem.Location]
                    self.itemattrlist[newItem.Location] = newItem
                else:
                    item = self.itemattrlist[newItem.Location] 
                    while item.next is not None:
                        item = item.next
                    item.next = newItem
            elif child.tagName == 'Coop':
                self.coop = eval(XMLHelper.getText(child.childNodes), 
                                 globals(), globals())
            elif child.tagName == 'Outfit':
                if child.nodeType == Node.TEXT_NODE: continue
                self.outfitnumbering += 1
                outfitname = child.getAttribute('Name')
                active = child.getAttribute('Active')
                self.outfitlist.append( { None : outfitname } )
                if active == "1": self.currentOutfit = len(self.outfitlist) - 1
                for piecenode in child.childNodes:
                    if piecenode.nodeType == Node.TEXT_NODE: continue
                    piecename = piecenode.getAttribute('Location')
                    index = int(piecenode.getAttribute('Index'))
                    equipped = str(piecenode.getAttribute('Equipped'))
                    self.outfitlist[-1][piecename] = ( index, equipped, )

        self.Realm.setCurrentIndex(Realms.index(self.realm))
        self.realmChanged(Realms.index(self.realm))
        if AllBonusList[self.realm].has_key(self.charclass):
            self.CharClass.setCurrentIndex(
                               ClassList[self.realm].index(self.charclass))
            self.charClassChanged(ClassList[self.realm].index(self.charclass))
        if racename in AllBonusList[self.realm][self.charclass]['Races']:
            self.CharRace.setCurrentIndex(
                              AllBonusList[self.realm][self.charclass] \
                                                      ['Races'].index(racename))
            self.raceChanged('')

        if len(self.outfitlist) < 1:
            self.appendOutfit()
        else:
            self.OutfitName.blockSignals(True)
            for outfit in self.outfitlist:
                self.OutfitName.addItem(outfit[None])
            self.OutfitName.setCurrentIndex(self.currentOutfit)
            self.OutfitName.blockSignals(False)
            self.outfitNameSelected(self.currentOutfit)

        self.deleteOutfitAction.setEnabled(len(self.outfitlist) > 1)
        self.modified = False
        self.nocalc = False
        self.restoreItem(self.itemattrlist[self.currentTabLabel])
        
    def chooseXMLUIFile(self):
        filters = "UI XML Templates (*.xsl *.xslt);;All Files (*.*)"
        filename = QFileDialog.getOpenFileName(self, "Choose UI Window Format",
                       self.ReportPath, filters)
        filename = unicode(filename)
        if filename is not None and str(filename) != '':
            self.UiReportFile = os.path.abspath(filename)
            #if templates are in one path, do we really want to
            #assume the report files would be saved to the same?
            #
            #self.ReportPath = os.path.dirname(self.UiReportFile)

    def generateUIXML(self):
        UIXML.uixml(self, self.UiReportFile)
   
    def loadRecentFile(self, action):
        index = action.data().toInt()[0]
        self.openFile(self.recentFiles[index], True)

    def openOptions(self):
        self.nocalc = True
        self.saveOptions()
        res = Options.Options(self).exec_()
        if res == 1:
            self.loadOptions()
            self.showcapmenuid.setChecked(self.capDistance)
            self.realmChanged(self.Realm.currentIndex())
            #self.modified = True
            self.nocalc = False
            self.restoreItem(self.itemattrlist[self.currentTabLabel])
        else:
            self.nocalc = False
            self.calculate()

    def openCraftWindow(self):
        CW = CraftWindow.CraftWindow(self, '', 1)
        CW.loadgems(list(self.itemattrlist[self.currentTabLabel].slots()))
        CW.exec_()
        self.restoreItem(self.itemattrlist[self.currentTabLabel])
        self.modified = True

    def gemClicked(self, item, slot):
        CW = CraftWindow.CraftWindow(self, '', 1)
        CW.loadgems([self.itemattrlist[self.currentTabLabel].slot(slot - 1)],)
        CW.exec_()
        self.restoreItem(self.itemattrlist[self.currentTabLabel])
        self.modified = True
    
    def openMaterialsReport(self):
        RW = ReportWindow.ReportWindow(self, '', 1)
        RW.materialsReport(self.itemattrlist)
        RW.exec_()

    def openConfigReport(self):
        RW = ReportWindow.ReportWindow(self, '', 1)
        RW.parseConfigReport(self.ReportFile, self.asXML(True))
        RW.exec_()

    def chooseReportFile(self):
        filters = "Report Templates (*.xsl *.xslt);;All Files (*.*)"
        filename = QFileDialog.getOpenFileName(self, "Choose Report Format",
                       self.ReportPath, filters)
        filename = unicode(filename)
        if filename is not None and str(filename) != '':
            self.ReportFile = os.path.abspath(filename)
            #if templates are in one path, would we really want to
            #assume the report files will be saved to the same?
            #
            #self.ReportPath = os.path.dirname(self.ReportFile)

    def openCraftBars(self):
        CB = CraftBar.CraftBar(self, '', 1)
        CB.exec_()

    def delveItemsDialog(self, find, findtype = None):
        locs = []
        finddesc = findtype
        if findtype is not None:
            if (find == 'AF' or find == 'Fatigue' or find == '% Power Pool'):
                findtype = None
            else:
                findtype = findtype[-5:]
        for key, item in self.itemattrlist.iteritems():
            activestate = item.ActiveState
            for slot in range(0, item.slotCount()):
                slottype = str(item.slot(slot).type())
                if slottype == 'Unused': continue
                effect = item.slot(slot).effect()
                if findtype is not None:
                    if slottype[-5:] != findtype: continue
                elif effect != 'AF' and effect != 'Fatigue' and effect != '% Power Pool':
                    if slottype == 'Resist': continue
                    if slottype[-5:] == 'Bonus': continue
                if effect != find:
                    if find == 'Power' or find == '% Power Pool':
                       if effect != 'Power' and effect != '% Power Pool':
                           continue
                    elif effect == 'Acuity':
                       if not find in AllBonusList[self.realm] \
                                                  [self.charclass][effect]:
                           continue
                    elif (slottype == 'Skill' or slottype == 'Focus') and \
                       effect[0:4] == 'All ' and \
                       AllBonusList[self.realm][self.charclass].has_key(effect):
                        if not find in AllBonusList[self.realm] \
                                                   [self.charclass][effect]:
                            continue
                    elif (((find == 'Archery and Casting Speed')
                           and effect in ('Casting Speed', 'Archery Speed')) 
                       or ((find == 'Archery and Spell Damage')
                           and effect in ('Spell Damage', 'Archery Damage'))
                       or ((find == 'Archery and Spell Range')
                           and effect in ('Spell Range', 'Archery Range'))):
                        pass
                    else:
                        continue
                amount = item.slot(slot).amount()
                if slottype == 'Focus':
                    amount += ' Levels Focus'
                if effect != find: 
                    amount += ' ' + effect
                if slottype == 'Cap Increase':
                    amount += ' Cap'
                locs.append([key, amount])
        DW = DisplayWindow.DisplayWindow(self)
        if findtype:
            DW.setWindowTitle('Slots With %s %s' % (find, finddesc))
        else:
            DW.setWindowTitle('Slots With %s' % find)
        DW.loadLocations(locs)
        DW.exec_()

    def mousePressEvent(self, e):
        if e is None: return
        child = self.childAt(e.pos())
        if child is None: return
        if not isinstance(child, QLabel): return
        if str(child.text()) == '': return
        shortname = str(child.objectName())
        nameidx = 2
        while nameidx < len(shortname):
            if shortname[nameidx] < 'a' or shortname[nameidx] > 'z':
                shorttype = shortname[nameidx:]
                shortname = shortname[0:nameidx]
            nameidx += 1
        if shortname in ['Gem', 'Points', 'Cost', 'Name']:
            slotid = child.objectName()[-2:]
            if str(slotid[0:1]) == '_':
                slotid = slotid[1:]
            item = self.itemattrlist[self.currentTabLabel]
            slot = int(slotid)
            if item.slot(slot).slotType() == 'player':
                self.gemClicked(self.currentTabLabel, slot)
            return
        if shortname in ['', 'Label', 'Total', 'Item']: return
        if child.parent().objectName() == 'GroupResists':
           self.delveItemsDialog(shortname, 'Resist')
        else:
           self.delveItemsDialog(shortname)

    def skillClicked(self,index):
        effect = str(index.data(Qt.DisplayRole).toString())
        bonus = str(index.data(Qt.UserRole).toString())
        if effect[-6:] == ' (PvE)' or effect[-6:] == ' Focus':
            effect = effect[:-6]
        if effect[-1:] == ')':
            amount, effect = string.split(effect.lstrip()[:-1], ' ', 1)
            ignore, amount = string.split(amount, '(', 1)
        else:
            amount, effect = string.split(effect.lstrip(), ' ', 1)
        self.delveItemsDialog(effect, bonus)

    def showCap(self):
        self.capDistance = not self.capDistance
        self.showcapmenuid.setChecked(self.capDistance)
        ScOptions.instance().setOption('DistanceToCap', self.capDistance)
        self.calculate()

    def swapWith(self, action):
        cur = self.itemattrlist[self.currentTabLabel]
        if cur.ActiveState != 'player': return
        piece = str(action.text())
        part = self.itemattrlist[piece]
        if cur == part: return
        prev = None
        while part.ActiveState != 'player':
            if part.next is None: 
                QMessageBox.critical(None, 'Error!', 'There is no crafted ' \
                    + piece + ' to swap gems with.  Create a new crafted ' \
                    + piece + ' and try again.', 'OK')
                return
            prev = part
            part = part.next
        if prev is not None:
            if self.itemattrlist[piece].Equipped == '1':
                self.itemattrlist[piece] = '0'
                part.Equipped = '1'
            prev.next = part.next
            part.next = self.itemattrlist[piece]
            self.itemattrlist[piece] = part
        for i in range(0,min(cur.slotCount(),part.slotCount())):
            if cur.slot(i).slotType() != 'player' \
                    or part.slot(i).slotType()  != 'player':
                continue
            itemslot = cur.itemslots[i]
            cur.itemslots[i] = part.itemslots[i]
            part.itemslots[i] = itemslot
        self.modified = True
        self.restoreItem(self.itemattrlist[self.currentTabLabel])

    def moveTo(self, action):
        cur = self.itemattrlist[self.currentTabLabel]
        piece = str(action.text())
        part = self.itemattrlist[piece]
        if cur == part: return
        if cur.next is None:
            item = Item(realm=self.realm,loc=self.currentTabLabel,
                        state=cur.ActiveState)
            if cur.ActiveState == 'drop':
                item.ItemName = "Drop Item" + str(self.itemnumbering)
            else:
                item.ItemName = "Crafted Item" + str(self.itemnumbering)
            self.itemnumbering += 1
            self.itemattrlist[self.currentTabLabel] = item
        else:
            self.itemattrlist[self.currentTabLabel] = cur.next
        if cur.Equipped == '1':
            self.itemattrlist[self.currentTabLabel].Equipped = '1'
        if part.Equipped == '1':
            part.Equipped = '0'
            cur.Equipped = '1'
        else:
            cur.Equipped = '1'
        cur.next = part
        cur.Location = piece
        self.itemattrlist[piece] = cur
        for outfit in self.outfitlist:
             outfititem = outfit[self.currentTabLabel]
             if outfititem[0] == cur.TemplateIndex:
                 outfit[self.currentTabLabel] = (
                     self.itemattrlist[self.currentTabLabel].TemplateIndex,
                     self.itemattrlist[self.currentTabLabel].Equipped,)
        self.outfitlist[self.currentOutfit][piece] = (cur.TemplateIndex,
                                                      cur.Equipped,)
        self.currentTabLabel = piece
        if piece in JewelTabList:
            row = 1
            col = JewelTabList.index(piece)
        else:
            row = 0
            col = PieceTabList.index(piece)
        self.modified = True
        self.PieceTab.setCurrentIndex(row, col)

    def chooseItemType(self, action):
        newtype = str(action.data().toString())
        item = self.itemattrlist[self.currentTabLabel]
        if newtype == 'Normal Item' or newtype == 'Enhanced Bow':
            if newtype == 'Normal Item':
                item.slot(4).setSlotType('effect')
            else:
                item.slot(4).setSlotType('crafted')
            if item.slot(5).type()[-6:] == "Effect":
                item.slot(4).setAll(item.slot(5).type(), item.slot(5).amount(), 
                             item.slot(5).effect(), item.slot(5).requirement())
            item.slot(5).setType('Unused')
            item.slot(5).setSlotType('unused')
        else:
            item.slot(4).setSlotType('crafted')
            if newtype[:9] == 'Legendary':
                item.slot(5).setSlotType('crafted')
            else:
                item.slot(5).setSlotType('effect')
            if item.slot(4).type()[-6:] == 'Effect':
                item.slot(5).setAll(item.slot(4).type(), item.slot(4).amount(), 
                             item.slot(4).effect(), item.slot(4).requirement())
                item.slot(4).setType('Unused')

        if newtype == 'Caster Staff' or newtype == 'Legendary Staff':
            for fixslot in item.slots():
                if fixslot.type() == 'Focus':
                    if (item.slot(3).slotType() == 'player'
                    and item.slot(3).type() != 'Unused'
                    and item.slot(3).type() != 'Focus'
                    and fixslot.slotType() == 'player'
                    and newtype == 'Legendary Staff'):
                        # Replace an existing Focus slot with the 4th slot's bonus
                        fixslot.setAll(item.slot(3).type(), item.slot(3).amount(), 
                                      item.slot(3).effect(),)
                    else:
                        fixslot.setType('Unused')

        if newtype == 'Caster Staff':
            item.slot(3).setSlotType('player')
            item.slot(4).setAll('Focus', '50', 'All Spell Lines')
        elif newtype == 'Legendary Staff':
            item.slot(3).setSlotType('crafted')
            item.slot(3).setAll('Focus', '50', 'All Spell Lines')
            item.slot(4).setAll('Other Bonus', '2', 'Archery and Spell Damage', 
                                requirement="vs All Monsters")
            item.slot(5).setSlotType('crafted')
            item.slot(5).setAll('Charged Effect', '60', 'Dmg w/Resist Debuff (Fire)', 
                                requirement="Level 50")
        elif newtype == 'Enhanced Bow':
            item.slot(3).setSlotType('player')
            item.slot(4).setSlotType('crafted')
            item.slot(4).setAll('Offensive Effect', '20', 'Direct Damage (Fire)')
        elif newtype == 'Legendary Bow':
            item.slot(3).setSlotType('crafted')
            item.slot(3).setAll('Other Bonus', '2', 'Archery and Spell Damage', 
                                requirement="vs All Monsters")
            item.slot(4).setAll('Other Bonus', '10', 'AF')
            item.slot(5).setSlotType('crafted')
            item.slot(5).setAll('Offensive Effect', '25', 'Dmg w/Resist Debuff (Fire)',
                                requirement="Level 50")
        elif newtype == 'Legendary Weapon':
            item.slot(3).setSlotType('crafted')
            item.slot(3).setAll('Other Bonus', '2', 'Melee Damage', 
                                requirement="vs All Monsters")
            item.slot(4).setAll('Other Bonus', '10', 'AF')
            item.slot(5).setSlotType('crafted')
            item.slot(5).setAll('Offensive Effect', '60', 'Dmg w/Resist Debuff (Fire)',
                                requirement="Level 50")
        else:
            item.slot(3).setSlotType('player')

        # Recover from previously legendary items
        if item.slot(3).slotType() == 'player' and \
                not item.slot(3).crafted():
            item.slot(3).setType('Unused')
        self.restoreItem(item)

    def newItemType(self, action):
        newtype = str(action.data().toString())
        if newtype == 'Drop Item':
            item = Item('drop', self.currentTabLabel, self.realm, self.itemIndex)
            item.ItemName = "Drop Item" + str(self.itemnumbering)
        else:
            item = Item('player', self.currentTabLabel, self.realm, self.itemIndex)
            item.ItemName = "Crafted Item" + str(self.itemnumbering)
        self.itemIndex += 1
        self.itemnumbering += 1
        item.next = self.itemattrlist[self.currentTabLabel]
        self.itemattrlist[self.currentTabLabel] = item
        self.outfitlist[self.currentOutfit][self.currentTabLabel] \
                  = ( item.TemplateIndex, item.Equipped, )
        if newtype == 'Drop Item' or newtype == 'Normal Item':
            self.restoreItem(item)
        else:
            self.chooseItemType(action)

    def addItem(self, item):
        if item.Location[-4:] == 'Ring':
            locations = ('Left Ring', 'Right Ring', 'Spare',)
        elif item.Location[-5:] == 'Wrist':
            locations = ('Left Wrist', 'Right Wrist', 'Spare',)
        elif ((item.TYPE in ItemTypes['Left Hand'][item.Realm])
              or (item.TYPE in ItemTypes['2 Handed'][item.Realm])):
            # Items in the left hand or two hand list might also be
            # in the ranged or right hand list, let's offer them...
            locations = []
            for test in ('Left Hand','Right Hand','2 Handed','Ranged',):
                if item.TYPE in ItemTypes[test][item.Realm]:
                    locations.append(test)
            locations.append('Spare')
        elif item.Location in TabList:
            locations = (str(item.Location), 'Spare',)
        else:
            locations = ('Spare',)
        chooseItemSlot = ChooseSlot.ChooseSlot(self.window(), locations)
        slot = chooseItemSlot.exec_()
        if slot < 0:
            return
        else:
            item.Location = locations[slot]
        self.modified = True
        item.TemplateIndex = self.itemIndex
        self.itemIndex += 1
        self.itemnumbering += 1
        item.next = self.itemattrlist[item.Location]
        item.Equipped = item.next.Equipped
        item.next.Equipped = '0'
        self.itemattrlist[item.Location] = item
        self.outfitlist[self.currentOutfit][item.Location] \
                  = ( item.TemplateIndex, item.Equipped, )
        idx = self.PieceTab.index(item.Location)
        if idx:
            self.PieceTab.setCurrentIndex(idx)

    def viewToolbar(self, action):
        view = action.data().toInt()[0]
        for act in self.viewtoolbarmenu.actions():
            if act.data().toInt()[0] == view:
                if not act.isChecked():
                    act.setChecked(True)
                    return
            else:
                if act.isChecked():
                    act.setChecked(False)
        if view == 0:
            self.toolbar.hide()
        else:
            self.setIconSize(QSize(view,view))
            self.toolbar.show()

    def appendOutfit(self):
        outfitname = 'Outfit%d' % self.outfitnumbering
        self.outfitnumbering += 1

        self.outfitlist.append( { None: outfitname } )
        idx = len(self.outfitlist) - 1

        self.currentOutfit = idx
        if idx != -1 and idx < len(self.outfitlist):
            for key, item in self.itemattrlist.iteritems():
                self.outfitlist[idx][key] = ( item.TemplateIndex, item.Equipped )
        self.OutfitName.blockSignals(True)
        self.OutfitName.addItem(outfitname)
        self.OutfitName.blockSignals(False)

    def newOutfit(self):
        f = QApplication.focusWidget()
        if f is not None: f.setFocus()
        self.appendOutfit()
        self.OutfitName.setCurrentIndex(self.currentOutfit)
        if len(self.outfitlist) > 1:
            self.deleteOutfitAction.setEnabled(True)
        self.modified = True

    def deleteOutfit(self):
        if self.currentOutfit < 0 or len(self.outfitlist) < 2: return
        outfit = self.currentOutfit
        self.currentOutfit = 0
        del self.outfitlist[outfit]
        self.OutfitName.blockSignals(True)
        self.OutfitName.removeItem(outfit)
        self.OutfitName.setCurrentIndex(self.currentOutfit)
        self.OutfitName.blockSignals(False)
        self.modified = True
        if len(self.outfitlist) < 2:
            self.deleteOutfitAction.setEnabled(False)
        self.outfitNameSelected(self.currentOutfit)

    def outfitNameSelected(self, idx):
        if not isinstance(idx, int): return
        #if self.currentOutfit == idx: return
        #sys.stdout.write("Selected Outfit %d\n" % idx)
        self.currentOutfit = idx
        outfit = self.outfitlist[idx]
        for piece, indexes in outfit.iteritems():
            if piece is None: continue
            item = self.itemattrlist[piece]
            prev = None
            while item and item.TemplateIndex != indexes[0]:
                prev = item
                item = item.next
            if item: 
                if prev:
                    prev.next = prev.next.next
                    item.next = self.itemattrlist[piece]
                    self.itemattrlist[piece].Equipped = '0'
                    self.itemattrlist[piece] = item
                self.itemattrlist[piece].Equipped = indexes[1]
            else:
                self.outfitlist[idx][piece] = ( self.itemattrlist[piece].TemplateIndex, 
                                                self.itemattrlist[piece].Equipped, )
        if self.nocalc: return
        self.restoreItem(self.itemattrlist[self.currentTabLabel])

    def outfitNameEdited(self, a0=None):
        idx = self.currentOutfit
        # Ignore side-effect signal textEditChanged() prior to activated()
        if idx != self.OutfitName.currentIndex(): return
        # Don't update as we stumble upon a duplicate name, let them keep editing
        if self.OutfitName.findText(a0) > -1: return
        outfitname = unicode(self.OutfitName.currentText())
        self.outfitlist[idx][None] = outfitname
        # blockSignals will not have the desired effect, save/restore the cursor as they insert
        cursorpos = self.OutfitName.lineEdit().cursorPosition()
        self.OutfitName.setItemText(idx, outfitname)
        self.OutfitName.lineEdit().setCursorPosition(cursorpos)
        self.modified = True

    def aboutBox(self):
        splash = AboutScreen(parent=self,modal=True)
        splash.exec_()

    def ignoreMouseEvent(self, e):
        e.ignore()

    def resizeEvent(self, e):
        if str(QApplication.style().objectName()[0:9]).lower() == "macintosh":
            self.sizegrip.move(self.width() - 15, self.height() - 15)

    def ethinargTest(self):
        if not self.ethinargWindow:
            self.ethinargWindow = Ethinarg.EthinargTestWindow(self, None)
        self.ethinargWindow.show()
        self.ethinargWindow.setSearchDefaults(self.realm, self.charclass, 
            self.currentTabLabel)

if __name__ == '__main__':
    app = QApplication([])
    scw = ScWindow()

