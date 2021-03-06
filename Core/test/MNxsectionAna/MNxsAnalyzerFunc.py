#!/usr/bin/env python
import sys, os, time
sys.path.append(os.path.dirname(__file__))

import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so")

ROOT.gSystem.Load("libRooUnfold.so")

ROOT.AutoLibraryLoader.enable()
from ROOT import edm, JetCorrectionUncertainty

from array import *
import cProfile

# please note that python selector class name (here: MNxsAnalyzer) 
# should be consistent with this file name (MNxsAnalyzer.py)

# you have to run this file from directory where it is saved

import CommonFSQFramework.Core.ExampleProofReader
from  CommonFSQFramework.Core.BetterJetGetter import BetterJetGetter

from optparse import OptionParser

from HLTMCWeighter import HLTMCWeighter
#import DiJetBalancePlugin

import math
class MNxsAnalyzer(CommonFSQFramework.Core.ExampleProofReader.ExampleProofReader):
    def init( self):
        if not self.isData:
            #self.hltMCWeighter = HLTMCWeighter("HLT_Jet15U")
            self.HLTMCWeighterJ15Raw = HLTMCWeighter("HLT_Jet15U_raw")
            self.HLTMCWeighterJ15L1Raw = HLTMCWeighter("HLT_Jet15U_L1Seeding_raw")
            self.HLTMCWeighterJ15FBL1Raw = HLTMCWeighter("HLT_DoubleJet15U_ForwardBackward_L1Seeding_raw")
            self.HLTMCWeighterJ15FBRaw = HLTMCWeighter("HLT_DoubleJet15U_ForwardBackward_raw")

        self.normFactor = self.getNormalizationFactor()


        #sys.stdout = sys.stderr
        #self.pr = cProfile.Profile()
        print "XXX init - MNxsAnalyzer", self.datasetName, self.isData

        self.todoShifts = ["_central"]
        if not self.isData and self.doPtShiftsJEC:
            self.todoShifts.append("_jecUp")
            self.todoShifts.append("_jecDown")

        if not self.isData and self.doPtShiftsJER:
            self.todoShifts.append("_jerUp")
            self.todoShifts.append("_jerDown")

        self.hist = {}
        todoTrg = ["_jet15", "_dj15fb"]

        binningDeta = (19, 0, 9.5)

        for shift in self.todoShifts:
            for trg in todoTrg:
                t = shift+trg
                self.hist["ptLead"+t] =  ROOT.TH1F("ptLead"+t,   "ptLead"+t,  100, 0, 100)
                self.hist["ptSublead"+t] =  ROOT.TH1F("ptSublead"+t,   "ptSublead"+t,  100, 0, 100)
                self.hist["etaLead"+t] =  ROOT.TH1F("etaLead"+t,   "etaLead"+t,  100, -5, 5)
                self.hist["etaSublead"+t] =  ROOT.TH1F("etaSublead"+t,   "etaSublead"+t,  100, -5, 5)
                self.hist["xsVsDeltaEta"+t] =  ROOT.TH1F("xs"+t,   "xs"+t, binningDeta[0], binningDeta[1], binningDeta[2])

                self.hist["xsVsDeltaEtaGen"+t] =  ROOT.TH1F("xsGen"+t,   "xsGen"+t, binningDeta[0], binningDeta[1], binningDeta[2])
                self.hist["xsVsDeltaEtaFake"+t] =  ROOT.TH1F("xsFake"+t,   "xsFake"+t, binningDeta[0], binningDeta[1], binningDeta[2])
                self.hist["xsVsDeltaEtaMiss"+t] =  ROOT.TH1F("xsMiss"+t,   "xsMiss"+t, binningDeta[0], binningDeta[1], binningDeta[2])

                self.hist["vtx"+t] =  ROOT.TH1F("vtx"+t,   "vtx"+t,  10, -0.5, 9.5)

                if self.unfoldEnabled:
                    self.hist["response"+t]= ROOT.RooUnfoldResponse(binningDeta[0], binningDeta[1], binningDeta[2], "response"+t,"response"+t)


        self.hist["evcnt"] =  ROOT.TH1F("evcnt_central_jet15", "evcnt_central_jet15",  1, -0.5, 0.5)
        #self.hist["detaGen"] =  ROOT.TH1F("detaGen_central_sum", "detaGen_central_sum",  binningDeta[0], binningDeta[1], binningDeta[2])

        # in principle trigger does not applies to gen plots. We keep consistent naming though, so the unfolded result to gen level plots is possible
        # in each category
        self.hist["detaGen_jet15"] =  ROOT.TH1F("detaGen_central_jet15", "detaGen_central_jet15",  binningDeta[0], binningDeta[1], binningDeta[2])
        self.hist["detaGen_dj15fb"] =  ROOT.TH1F("detaGen_central_dj15fb", "detaGen_central_dj15fb",  binningDeta[0], binningDeta[1], binningDeta[2])
        self.hist["detaGenVsRec"] =  ROOT.TH2F("detaGenVsRec_central_jet15", "detaGenVsRec_central_jet15",\
                                               binningDeta[0]*20, binningDeta[1], binningDeta[2],\
                                               binningDeta[0]*20, binningDeta[1], binningDeta[2])


        if self.onlyPtHatReweighing:
            self.var = {}
            self.var["leadPt"] = array('d', [0])
            self.var["leadEta"] = array('d', [0])
            self.var["weight"] = array('d', [0]) # only jet15 trigger??
            #self.var["alphaQCD"] = array('d', [0])
            self.var["qScale"]   = array('d', [0])
            self.tree = ROOT.TTree("data", "data")
            for v in self.var:
                self.tree.Branch(v, self.var[v], v+"/D")
            self.addToOutput(self.tree)

        else:
            for h in self.hist:
                if not h.startswith("response"):
                    self.hist[h].Sumw2()
                #self.GetOutputList().Add(self.hist[h])
                self.addToOutput(self.hist[h])

        if self.applyPtHatReweighing and not self.isData:
                fp = "CommonFSQFramework.Core/test/MNxsectionAna/"
                todo = ["ptHatWeighters.root"]
                #todo = ["ptHatWeighters_invx_pass1.root_invX", 
                #        "ptHatWeighters_invx_pass2.root_invX",
                #        "ptHatWeighters_invx_pass3.root_invX",]
                self.ptHatW = []
                for t in todo:
                    ptHatFileName = edm.FileInPath("CommonFSQFramework.Core/test/MNxsectionAna/"+t).fullPath()
                    ptHatFile = ROOT.TFile(ptHatFileName)
                    self.ptHatW.append(ptHatFile.Get(self.datasetName+"/ptHatW"))
                    #print "PTHat weighter set to", self.datasetName+"/ptHatW"
                    #print "PTHat test@30:", self.ptHatW.Eval(30)




        puFiles = {}
        # CommonFSQFramework.Core/test/MNxsectionAna/
        jet15FileV2 = edm.FileInPath("CommonFSQFramework/Core/test/MNxsectionAna/data/PUJet15V2.root").fullPath()   # MC gen distribution

        puFiles["dj15_1"] = edm.FileInPath("CommonFSQFramework/Core/test/MNxsectionAna/data/pu_dj15_1_0.root").fullPath()
        puFiles["dj15_1_05"] = edm.FileInPath("CommonFSQFramework/Core/test/MNxsectionAna/data/pu_dj15_1_05.root").fullPath()
        puFiles["dj15_0_95"] = edm.FileInPath("CommonFSQFramework/Core/test/MNxsectionAna/data/pu_dj15_0_95.root").fullPath()
        puFiles["j15_1"] = edm.FileInPath("CommonFSQFramework/Core/test/MNxsectionAna/data/pu_j15_1_0.root").fullPath()
        puFiles["j15_1_05"] = edm.FileInPath("CommonFSQFramework/Core/test/MNxsectionAna/data/pu_j15_1_05.root").fullPath()
        puFiles["j15_0_95"] = edm.FileInPath("CommonFSQFramework/Core/test/MNxsectionAna/data/pu_j15_0_95.root").fullPath()

        self.lumiWeighters = {}
        self.lumiWeighters["_jet15_central"] = edm.LumiReWeighting(jet15FileV2, puFiles["j15_1"], "MC", "pileup")
        self.lumiWeighters["_jet15_puUp"] = edm.LumiReWeighting(jet15FileV2, puFiles["j15_1_05"], "MC", "pileup")
        self.lumiWeighters["_jet15_puDown"] = edm.LumiReWeighting(jet15FileV2, puFiles["j15_0_95"], "MC", "pileup")

        self.lumiWeighters["_dj15fb_central"] = edm.LumiReWeighting(jet15FileV2, puFiles["dj15_1"], "MC", "pileup")
        self.lumiWeighters["_dj15fb_puUp"] = edm.LumiReWeighting(jet15FileV2, puFiles["dj15_1_05"], "MC", "pileup")
        self.lumiWeighters["_dj15fb_puDown"] = edm.LumiReWeighting(jet15FileV2, puFiles["dj15_0_95"], "MC", "pileup")

        #self.jetGetter = JetGetter("PF")
        #if hasattr(self, "jetUncFile"):
        #    self.jetGetter.setJecUncertainty(self.jetUncFile)

        self.jetGetter = BetterJetGetter("PFAK5") 



    def dr(self, a,b):
        de = a.eta()-b.eta()
        dp = a.phi()-b.phi()
        pi = 3.1415
        if dp > pi: dp -= 2*pi
        if dp < -pi: dp += 2*pi
        #print  a.phi(), b.phi(), dp

        return math.sqrt(de*de+dp*dp)


    def doGri(self, weight, variation):
        fil = lambda x: x.pt() > self.threshold and abs(x.eta())<4.7
        genJ = filter(fil, self.fChain.genJets) # 1
        detJ  =filter(fil, self.jetGetter.get(variation)) #1

        ##print "AAA", len(genJ), len(detJ)

        postfix = variation+"_jet15"
        if len(genJ)<2: 
            if len(detJ) < 2:
                return
            detJB = min(detJ, key= lambda j: j.eta()  )
            detJF = max(detJ, key= lambda j: j.eta()  )
            deta = abs(detJB.eta()-detJF.eta())
            self.hist["xsVsDeltaEtaFake"+postfix].Fill(deta, weight)
            return # 2

        gjB = min(genJ, key= lambda j: j.eta()  )
        gjF = max(genJ, key= lambda j: j.eta()  )
        detaGen = gjF.eta() - gjB.eta()
        self.hist["xsVsDeltaEtaGen"+postfix].Fill(detaGen, weight)  # 3
        if len(detJ)<2:
            self.hist["xsVsDeltaEtaMiss"+postfix].Fill(detaGen, weight) # 4
            self.hist["response"+postfix].Miss(detaGen, weight)
            return

        closestDetJet1 = min(detJ, key = lambda j: self.dr(j, gjB) ) # 5, eta restriction imposed in step 1
        dr1 = self.dr(closestDetJet1, gjB)
        if dr1 > 0.3:
            self.hist["xsVsDeltaEtaMiss"+postfix].Fill(detaGen, weight) # 6
            self.hist["response"+postfix].Miss(detaGen, weight)
            return
        else:
            closestDetJet2 = min(detJ, key = lambda j: self.dr(j, gjF) ) # 5,
            dr2 = self.dr(closestDetJet2, gjF)
            if dr2 > 0.3:
                self.hist["xsVsDeltaEtaMiss"+postfix].Fill(detaGen, weight) # 6
                self.hist["response"+postfix].Miss(detaGen, weight)
                return

        detaDet = abs(closestDetJet1.eta()- closestDetJet2.eta())
        self.hist["response"+postfix].Fill(detaDet, detaGen, weight) # 7




    # note: for the ptHat reweighing we will do only the central variation.
    #       otherwise the changes from the JEC/JER variations would be fixed
    #       by the ptHat reweighing procedure

    #
    # leadPt:qScale gives a nice linear response
    #
    # todo: trigger correction for data
    def doPtHatReweighing(self, weightBase):
        if self.isData:
            if self.fChain.jet15 < 0.5:
                return
            weight = weightBase
        else:
            if not self.triggerFired("_jet15"):
                return
            truePU = self.fChain.puTrueNumInteractions
            puWeight =  self.lumiWeighters["_jet15_central"].weight(truePU)
            weight = weightBase*puWeight

        sortKey = lambda j: j.pt()*(j.pt()>self.threshold)\
                          *(j.jetid()>0.5)*(abs(j.eta())<4.7)

        # if empty sequence...
        try:
            bestJet = max(self.jetGetter.get("_central"), key=sortKey)
        except ValueError:
            return

        if not sortKey(bestJet): return # do we really have a jet passing the criteria?
        pt, eta =  bestJet.pt(), bestJet.eta()
        self.var["leadPt"][0] = pt
        self.var["leadEta"][0] = eta
        self.var["weight"][0] = weight
        if not self.isData:
            #self.var["alphaQCD"][0] = self.fChain.alphaQCD
            self.var["qScale"][0] = self.fChain.qScale
        self.tree.Fill()

        
    def triggerFired(self, case):
        if case == "_jet15" and self.MC_jet15_triggerFired_cached != None:
            return self.MC_jet15_triggerFired_cached
        if case == "_dj15fb" and self.MC_dj15fb_triggerFired_cached != None:
            return self.MC_dj15fb_triggerFired_cached

        ev = self.fChain.event
        rnd4eff = ev%10000/9999.

        if case == "_jet15":
            self.HLTMCWeighterJ15L1Raw.newEvent(self.fChain)
            self.HLTMCWeighterJ15Raw.newEvent(self.fChain)
            w1 = self.HLTMCWeighterJ15L1Raw.getWeight()
            w2 = self.HLTMCWeighterJ15Raw.getWeight()
            self.MC_jet15_triggerFired_cached = w1*w2 > rnd4eff
            return self.MC_jet15_triggerFired_cached
        elif case == "_dj15fb":
            self.HLTMCWeighterJ15FBL1Raw.newEvent(self.fChain)
            self.HLTMCWeighterJ15FBRaw.newEvent(self.fChain)
            w1 = self.HLTMCWeighterJ15FBL1Raw.getWeight()
            w2 = self.HLTMCWeighterJ15FBRaw.getWeight()
            self.MC_dj15fb_triggerFired_cached = w1*w2 > rnd4eff
            return self.MC_dj15fb_triggerFired_cached
        else:
            raise Excecption("triggerFired: case not known: "+str(case))
        
           

    def analyze(self):
        self.MC_jet15_triggerFired_cached = None
        self.MC_dj15fb_triggerFired_cached = None

        self.hist["evcnt"].Fill(0)
        if self.fChain.ngoodVTX == 0: return
        self.jetGetter.newEvent(self.fChain)
        weightBase = 1. 
        if not self.isData:
            weightBase *= self.fChain.genWeight*self.normFactor 

            #print ev, w1*w2, rnd4eff, triggerFired


        if not self.isData and  self.applyPtHatReweighing:
            ptHat = self.fChain.qScale
            w = 1.
            for weighter in self.ptHatW:
                w*=max(weighter.Eval(ptHat), 0.)
                #print "W:", ptHat, weighter.Eval(ptHat)
            weightBase *= w
 

        if self.onlyPtHatReweighing:
            self.doPtHatReweighing(weightBase)
            return
           

        # fill the roounfoldresponse
        if not self.isData:
            genDEta = None
            genTopology = None
            etas = []
            for j in self.fChain.genJets:
                if j.pt() < self.threshold: continue
                eta = j.eta()
                if abs(j.eta())>4.7: continue
                etas.append(eta)
            if len(etas)>1:
                fwd = max(etas)
                bkw = min(etas)
                genTopology = "CF"
                if fwd > 3 and bkw < -3:
                    genTopology = "FB"
                genDEta = fwd - bkw
                #self.hist["detaGen"].Fill(genDEta, weightBase) # basic gen level distribution shouldnt be PU dependent
                if genTopology == "FB":
                    self.hist["detaGen_dj15fb"].Fill(genDEta, weightBase) # basic gen level distribution shouldnt be PU dependent
                else:
                    self.hist["detaGen_jet15"].Fill(genDEta, weightBase) # basic gen level distribution shouldnt be PU dependent


        for shift in self.todoShifts:
            # Q&D warning: to test this you need to comment out all filling of the response object below
            #truePU = self.fChain.puTrueNumInteractions
            #puWeight =  self.lumiWeighters["_jet15_central"].weight(truePU)
            #self.doGri(weightBase*puWeight, shift)


            # find best dijet pair
            mostFwdJet = None
            mostBkgJet = None
            mostFwdJetEta = None
            mostBkgJetEta = None
            mostFwdJetPt = None
            mostBkgJetPt = None

            for jet in self.jetGetter.get(shift):
                #if jetID.at(i) < 0.5: continue
                if not jet.jetid(): continue
                eta =  jet.eta()
                if abs(eta) > 4.7: continue

                ptShifted = jet.pt()
                if ptShifted < self.threshold: continue

                if  mostFwdJet == None or mostFwdJetEta < eta:
                    mostFwdJet = jet
                    mostFwdJetEta = eta
                    mostFwdJetPt = ptShifted
                if  mostBkgJet == None or mostBkgJetEta > eta:
                    mostBkgJet = jet
                    mostBkgJetEta = eta
                    mostBkgJetPt = ptShifted

            pairFound = False
            if mostFwdJet != None and mostBkgJet != mostFwdJet:
                pairFound = True


            isMiss = True # mark if dijet pair was not found (needed to correctly fill response)
            # A dijet pair was found. Check trigger for data
            # fill histograms
            if pairFound:
                deta = abs(mostFwdJetEta - mostBkgJetEta)
                if not self.isData and genDEta:
                    if shift == "_central":
                        self.hist["detaGenVsRec"].Fill(genDEta, deta, weightBase)
                # detaGenVsRec

                triggerToUse = "_jet15"
                if abs(mostFwdJetEta) > 3 and abs(mostBkgJetEta) > 3 and mostFwdJetEta*mostBkgJetEta<0:
                    triggerToUse = "_dj15fb"

                # TODO: we need to separate gen level categories!!
                gotTrigger = True
                if self.isData: # check trigger
                    if triggerToUse == "_jet15":
                        gotTrigger = self.fChain.jet15 > 0.5
                    elif triggerToUse == "_dj15fb":
                        gotTrigger = self.fChain.doubleJ15FB > 0.5
                    else:
                        raise Exception("Trigger not known??? "+triggerToUse)
                else:
                    gotTrigger = self.triggerFired(triggerToUse)



                if gotTrigger:
                    # calculate weight for MC
                    weight = weightBase
                    if not self.isData:
                        truePU = self.fChain.puTrueNumInteractions
                        puWeight =  self.lumiWeighters[triggerToUse+"_central"].weight(truePU)
                        weight *= puWeight

                    histoName = shift +triggerToUse
                    self.hist["xsVsDeltaEta"+histoName].Fill(deta, weight)
                    if not self.isData:
                        isMiss = False
                        isCorrectTopo = (triggerToUse == "_jet15") and genTopology == "CF" or (triggerToUse == "_dj15fb") and genTopology == "FB"
                        #'''
                        if genDEta == None or not isCorrectTopo:    # fake pair, e.g. from bkg or we landed in a wrong category
                            if self.unfoldEnabled:
                                self.hist["response"+histoName].Fake(deta, weight)
                        else:
                            if self.unfoldEnabled:
                                self.hist["response"+histoName].Fill(deta, genDEta, weight)
                        #'''

                    # fill also some control plots
                    leadJet = mostBkgJet
                    subleadJet = mostFwdJet
                    ptLead =  mostBkgJetPt 
                    ptSublead = mostFwdJetPt
                    etaLead = mostBkgJetEta
                    etaSublead = mostFwdJetEta

                    if ptSublead > ptLead:
                        leadJet, subleadJet = subleadJet, leadJet
                        ptLead, ptSublead = ptSublead, ptLead
                        etaLead, etaSublead = etaSublead, etaLead

                    self.hist["vtx"+histoName].Fill(self.fChain.ngoodVTX, weight)
                    self.hist["ptLead"+histoName].Fill(ptLead, weight)
                    self.hist["ptSublead"+histoName].Fill(ptSublead, weight)
                    self.hist["etaLead"+histoName].Fill(etaLead, weight)
                    self.hist["etaSublead"+histoName].Fill(etaSublead, weight)

            if not self.isData and genDEta and isMiss:
                if genTopology == "CF":
                    triggerToUse = "_jet15"
                else:
                    triggerToUse = "_dj15fb"
                histoName = shift +triggerToUse
                weight = weightBase
                if not self.isData:
                    truePU = self.fChain.puTrueNumInteractions
                    puWeight =  self.lumiWeighters[triggerToUse+"_central"].weight(truePU)

                #print "Miss", triggerToUse, genDEta, shift
                #'''
                if self.unfoldEnabled:
                    self.hist["response"+histoName].Miss(genDEta, weight)
                #'''

    def finalize(self):
        print "Finalize:"

if __name__ == "__main__":
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    parser = OptionParser(usage="usage: %prog [options] filename",
                            version="%prog 1.0")

    parser.add_option("-p", "--ptHatReweighing",   action="store_true", dest="ptHatReweighing", \
                                help="produce tree for ptHat reweighing")

    (options, args) = parser.parse_args()

    sampleList = None
    maxFilesMC = None
    maxFilesData = None
    nWorkers = 12

    # debug config:
    #'''
    sampleList = []
    #sampleList= ["QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"]

    #sampleList.append("QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp")
    #'''
    sampleList.append("JetMETTau-Run2010A-Apr21ReReco-v1")
    sampleList.append("Jet-Run2010B-Apr21ReReco-v1")
    sampleList.append("JetMET-Run2010A-Apr21ReReco-v1")
    sampleList.append("METFwd-Run2010B-Apr21ReReco-v1")
    # '''
    # '''
    #maxFilesMC = 48
    #maxFilesMC = 2
    #maxFilesData = 1
    #nWorkers = 1
    #maxFilesMC = 16
    #nWorkers = 12
    nWorkers = 10

    slaveParams = {}
    slaveParams["threshold"] = 35.
    #slaveParams["doPtShiftsJEC"] = False
    slaveParams["doPtShiftsJEC"] = True

    #slaveParams["doPtShiftsJER"] = False
    slaveParams["doPtShiftsJER"] = True

    #slaveParams["jetID"] = "pfJets_jetID" # TODO

    slaveParams["unfoldEnabled"] = True

    if options.ptHatReweighing:
        slaveParams["onlyPtHatReweighing"] = True
        slaveParams["applyPtHatReweighing"] = False
        slaveParams["threshold"] = 30.
        ofile = "treesForPTHatReweighing.root"
        sampleList.remove("METFwd-Run2010B-Apr21ReReco-v1")
    else:
        slaveParams["onlyPtHatReweighing"] = False
        #slaveParams["applyPtHatReweighing"] = True
        slaveParams["applyPtHatReweighing"] = False
        ofile = "plotsMNxs.root"


    MNxsAnalyzer.runAll(treeName="mnXS",
                               slaveParameters=slaveParams,
                               sampleList=sampleList,
                               maxFilesMC = maxFilesMC,
                               maxFilesData = maxFilesData,
                               nWorkers=nWorkers,
                               usePickle = True,
                               useProofOFile = True,
                               outFile = ofile )

    print "TODO: fakes prob vs eta"
    print "TODO: larger statistics for herwig"
    print "TODO: better binning for det level plots"


