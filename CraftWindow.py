# CraftWindow.py: Dark Age of Camelot Spellcrafting Calculator
#
# See http://kscraft.sourceforge.net/ for updates
#
# See NOTICE.txt for copyrights and grant of license

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from B_CraftWindow import *
from constants import *
import SC

class CraftWindow(QDialog, Ui_B_CraftWindow):
    def __init__(self,parent = None,name = None,modal = False,fl = Qt.Widget):
        QDialog.__init__(self,parent,fl)
        Ui_B_CraftWindow.setupUi(self,self)
        if (name):
            self.setObjectName(name)
        if (modal):
            self.setModal(modal)
        self.gems = []
        self.GemName = []
        self.GemCost = []
        self.GemMakes = []
        for i in range (0, 4):
            idx = i + 1
            self.GemName.append(getattr(self, 'Gem%dName' % idx))
            self.GemCost.append(getattr(self, 'Gem%dCost' % idx))
            self.GemMakes.append(getattr(self, 'Gem%dMakes' % idx))
            # Hide '0' values
            self.GemMakes[i].setSpecialValueText(" ")
            self.connect(self.GemMakes[i],SIGNAL("valueChanged(int)"),self.RemakeChanged)
        self.connect(self.Close,SIGNAL("clicked()"),self.CloseWindow)
        self.parent = parent
        testfont = QFontMetrics(QApplication.font())
        width = testfont.size(Qt.TextSingleLine, "  199g 00s 00c").width()
        self.gridlayout.setColumnMinimumWidth(2,width)


    def loadgems(self, gems):
        materials = { 'Gems': { }, 'Dusts' : { }, 'Liquids' : { } }
        for slot in range(0, 4):
            while slot < len(gems) and (gems[slot].type() == 'Unused' 
                                     or gems[slot].slotType() != 'player'):
                del gems[slot]
        self.gems = gems
        for slot in range(0, 4):
            self.GemMakes[slot].setVisible(slot < len(gems))
            self.GemCost[slot].setVisible(slot < len(gems))
            self.GemName[slot].setVisible(slot < len(gems))

            if slot >= len(gems):
                continue

            self.GemMakes[slot].setValue(int(gems[slot].makes()))
            self.GemCost[slot].setText(SC.formatCost(gems[slot].gemCost(1)))
            self.GemName[slot].setText(gems[slot].gemName(self.parent.realm))
        self.computeMaterials()

    def computeMaterials(self):
        materials = { 'Used' : { 'Gems' : { }, 'Dusts' : {}, 'Liquids': {} },
            'Expected' : { 'Gems' : { }, 'Dusts' : {}, 'Liquids': {} } }
        totalcost = 0
        for slot in range(0, 4):
            if (slot >= len(self.gems)): continue
            totalcost += self.gems[slot].gemCost()
            for mattype, matl in self.gems[slot].gemMaterials(self.parent.realm).items():
                for mat, val in matl.items():
                    nummakes = int(self.gems[slot].makes())
                    if nummakes > 0:
                        if materials['Used'][mattype].has_key(mat):
                            materials['Used'][mattype][mat] += val * nummakes
                        else:
                            materials['Used'][mattype][mat] = val * nummakes
                    if materials['Expected'][mattype].has_key(mat):
                        materials['Expected'][mattype][mat] += val
                    else:
                        materials['Expected'][mattype][mat] = val
        self.TotalCost.setText(SC.formatCost(totalcost))
        for matctl, matlist in ((self.MatsUsed, materials['Used'],),
                                (self.MatsExpected, materials['Expected'],),):
            matctl.clear()
            for mat in MaterialGems:
                if (matlist['Gems'].has_key(mat)):
                    matctl.append("%d %s Gem" % (matlist['Gems'][mat], mat))
            for mattype in ('Liquids', 'Dusts',):
                matsorted = list(matlist[mattype].items())
                matsorted.sort()
                for mat, val in matsorted:
                    matctl.append("%d %s" % (val, mat))

    def RemakeChanged(self, val):
        i = int(self.sender().objectName()[3]) - 1
        self.gems[i].setMakes(str(val))
        self.computeMaterials()

    def CloseWindow(self):
        self.done(1)

