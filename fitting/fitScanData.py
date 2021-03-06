"""
``fitScanData`` --- S-curves fits
---------------------------------
"""

import numpy as np
import ROOT as r
from gempython.gemplotting.utils.anaInfo import dict_calSF

class DeadChannelFinder(object):
    def __init__(self):
        self.isDead = [ np.ones(128, dtype=bool) for i in range(24) ]

    def feed(self, event):
        self.isDead[event.vfatN][event.vfatCH] = False

class ScanDataFitter(DeadChannelFinder):
    def __init__(self, calDAC2Q_m=None, calDAC2Q_b=None, isVFAT3=False):
        """
        calDAC2Q_m - list of slope values for "fC = m * cal_dac + b" equation, ordered by vfat position
        calDAC2Q_b - as calDAC2Q_m but for intercept b
        isVFAT3 - if using VFAT3
        """

        super(ScanDataFitter, self).__init__()

        from gempython.utils.nesteddict import nesteddict as ndict
        r.gStyle.SetOptStat(0)

        self.Nev = ndict()
        self.scanFuncs  = ndict()
        self.scanHistos = ndict()
        self.scanHistosChargeBins = ndict()
        self.scanCount  = ndict()
        self.scanFitResults   = ndict()

        self.isVFAT3    = isVFAT3

        self.calDAC2Q_m = np.ones(24)
        if calDAC2Q_m is not None:
            self.calDAC2Q_m = calDAC2Q_m

        self.calDAC2Q_b = np.zeros(24)
        if calDAC2Q_b is not None:
            self.calDAC2Q_b = calDAC2Q_b

        for vfat in range(0,24):
            self.scanFitResults[0][vfat] = np.zeros(128)
            self.scanFitResults[1][vfat] = np.zeros(128)
            self.scanFitResults[2][vfat] = np.zeros(128)
            self.scanFitResults[3][vfat] = np.zeros(128)
            self.scanFitResults[4][vfat] = np.zeros(128)
            self.scanFitResults[5][vfat] = np.zeros(128)
            self.scanFitResults[6][vfat] = np.zeros(128, dtype=bool)
            for ch in range(0,128):
                self.scanCount[vfat][ch] = 0
                if self.isVFAT3:
                    self.scanFuncs[vfat][ch] = r.TF1('scurveFit_vfat%i_chan%i'%(vfat,ch),'[3]*TMath::Erf((TMath::Max([2],x)-[0])/(TMath::Sqrt(2)*[1]))+[3]',
                            self.calDAC2Q_m[vfat]*253+self.calDAC2Q_b[vfat],self.calDAC2Q_m[vfat]*1+self.calDAC2Q_b[vfat])
                    self.scanHistos[vfat][ch] = r.TH1D('scurve_vfat%i_chan%i_h'%(vfat,ch),'scurve_vfat%i_chan%i_h'%(vfat,ch),
                            254,self.calDAC2Q_m[vfat]*254.5+self.calDAC2Q_b[vfat],self.calDAC2Q_m[vfat]*0.5+self.calDAC2Q_b[vfat])
                else:
                    self.scanFuncs[vfat][ch] = r.TF1('scurveFit_vfat%i_chan%i'%(vfat,ch),'[3]*TMath::Erf((TMath::Max([2],x)-[0])/(TMath::Sqrt(2)*[1]))+[3]',
                            self.calDAC2Q_m[vfat]*1+self.calDAC2Q_b[vfat],self.calDAC2Q_m[vfat]*253+self.calDAC2Q_b[vfat])
                    self.scanHistos[vfat][ch] = r.TH1D('scurve_vfat%i_chan%i_h'%(vfat,ch),'scurve_vfat%i_chan%i_h'%(vfat,ch),
                            254,self.calDAC2Q_m[vfat]*0.5+self.calDAC2Q_b[vfat],self.calDAC2Q_m[vfat]*254.5+self.calDAC2Q_b[vfat])
                    pass
                self.scanHistosChargeBins[vfat][ch] = [self.scanHistos[vfat][ch].GetXaxis().GetBinLowEdge(binX) for binX in range(1,self.scanHistos[vfat][ch].GetNbinsX()+2) ] #Include overflow
                pass
            pass

        self.fitValid = [ np.zeros(128, dtype=bool) for vfat in range(24) ]

        return

    def feed(self, event):
        super(ScanDataFitter, self).feed(event)

        charge = self.calDAC2Q_m[event.vfatN]*event.vcal+self.calDAC2Q_b[event.vfatN]
        if self.isVFAT3: #v3 electronics
            if event.isCurrentPulse:
                #Q = CAL_DUR * CAL_DAC * 10nA * CAL_FS
                charge = (1./ 40079000) * event.vcal * (10 * 1e-9) * dict_calSF[event.calSF] * 1e15
                if(event.vcal > 254):
                    self.scanCount[event.vfatN][event.vfatCH] += event.Nhits
            else:
                charge = self.calDAC2Q_m[event.vfatN]*(event.vcal)+self.calDAC2Q_b[event.vfatN]
                if((256-event.vcal) > 254):
                    self.scanCount[event.vfatN][event.vfatCH] += event.Nhits
        else:
            if(event.vcal > 250):
                self.scanCount[event.vfatN][event.vfatCH] += event.Nhits
                pass
            pass

        from gempython.gemplotting.utils.anautilities import first_index_gt
        from math import sqrt
        chargeBin = first_index_gt(self.scanHistosChargeBins[event.vfatN][event.vfatCH], charge)-1
        self.scanHistos[event.vfatN][event.vfatCH].SetBinContent(chargeBin,event.Nhits)
        self.scanHistos[event.vfatN][event.vfatCH].SetBinError(chargeBin,sqrt(event.Nhits))
        self.Nev[event.vfatN][event.vfatCH] = event.Nev

        return

    def feedHisto(self, vfatN, vfatCH, histo, nEvts=None):
        self.scanHistos[vfatN][vfatCH] = histo
        self.isDead[vfatN][vfatCH] = False
        if nEvts is None:
            maxBin = self.scanHistos[vfatN][vfatCH].GetMaximumBin()
            self.Nev[vfatN][vfatCH] = self.scanHistos[vfatN][vfatCH].GetBinContent(maxBin)
        else:
            self.Nev[vfatN][vfatCH] = nEvts

        return

    def fit(self, debug=False):
        """
        Iteratively fits all scurves
        Note:   if the user supplied calDAC2Q_m and calDAC2Q_b at
                construction then output container will have relevant
                parameters in charge units instead of DAC units

        Returns self.scanFitResults
            
                 [0][vfat][ch] = scurve mean in either DAC units or charge (threshold of comparator)
                 [1][vfat][ch] = scurve width in either DAC units or charge (noise seen by comparator)
                 [2][vfat][ch] = scurve pedestal in hits (e.g. at 0 VCAL this is the noise)
                 [3][vfat][ch] = fitChi2
                 [4][vfat][ch] = self.scanCount[vfat][ch]
                 [5][vfat][ch] = fitNDF

        The TF1 is color coded:
            Black - Default
            Blue - Fit Converged 
            Gray - Dead channel or empty input histogram
            Orange - Fit result is empty
        """

        r.gROOT.SetBatch(True)
        r.gStyle.SetOptStat(0)

        random = r.TRandom3()
        random.SetSeed(0)
        for vfat in range(0,24):
            if self.isVFAT3:
                fitTF1 = r.TF1('myERF','[3]*TMath::Erf((TMath::Max([2],x)-[0])/(TMath::Sqrt(2)*[1]))+[3]',
                            self.calDAC2Q_m[vfat]*253+self.calDAC2Q_b[vfat],self.calDAC2Q_m[vfat]*1+self.calDAC2Q_b[vfat])
            else:
                fitTF1 = r.TF1('myERF','[3]*TMath::Erf((TMath::Max([2],x)-[0])/(TMath::Sqrt(2)*[1]))+[3]',
                            self.calDAC2Q_m[vfat]*1+self.calDAC2Q_b[vfat],self.calDAC2Q_m[vfat]*253+self.calDAC2Q_b[vfat])
            fitTF1.SetLineColor(r.kBlack)
            
            if not debug:
                print 'fitting vfat %i'%(vfat)

            for ch in range(0,128):
                if debug:
                    print 'fitting vfat %i chan %i'%(vfat,ch)
                
                if self.isDead[vfat][ch]:
                    fitTF1.SetLineColor(r.kGray)
                    continue # Don't try to fit dead channels
                elif not (self.scanHistos[vfat][ch].Integral() > 0):
                    fitTF1.SetLineColor(r.kGray)
                    continue # Don't try to fit with 0 entries
                
                fitChi2 = 0
                MinChi2Temp = 99999999
                stepN = 0
                
                if debug:
                    print "| stepN | vfatN | vfatCH | isVFAT3 | p0_low | p0 | p0_high | p1_low | p1 | p1_high | p2_low | p2 | p2_high |"
                    print "| ----- | ----- | ------ | ------- | ------ | -- | ------- | ------ | -- | ------- | ------ | -- | ------- |"
                while(stepN < 30):
                    #rand = max(0.0, random.Gaus(10, 5)) # do not accept negative numbers
                    rand = abs(random.Gaus(10, 5)) # take positive definite numbers

                    # Make sure the input parameters are positive
                    if rand > 100: continue
                    if (self.calDAC2Q_m[vfat]*(8+stepN*8)+self.calDAC2Q_b[vfat]) < 0:
                        stepN +=1
                        continue
                    #if (self.calDAC2Q_m[vfat]*(rand)+self.calDAC2Q_b[vfat]) < 0: continue

                    # Provide an initial guess
                    init_guess_p0 = self.calDAC2Q_m[vfat]*(8+stepN*8)+self.calDAC2Q_b[vfat]
                    init_guess_p1 = abs(self.calDAC2Q_m[vfat]*rand)  #self.calDAC2Q_m[vfat] might be negative (e.g. VFAT3 case)
                    init_guess_p2 = 0.
                    init_guess_p3 = self.Nev[vfat][ch]/2.

                    fitTF1.SetParameter(0, init_guess_p0)
                    fitTF1.SetParameter(1, init_guess_p1)
                    fitTF1.SetParameter(2, init_guess_p2)
                    fitTF1.SetParameter(3, init_guess_p3)

                    # Set Parameter Limits
                    if self.isVFAT3:
                        fitTF1.SetParLimits(0, self.calDAC2Q_m[vfat]*(256)+self.calDAC2Q_b[vfat], self.calDAC2Q_m[vfat]*(1)+self.calDAC2Q_b[vfat])
                        fitTF1.SetParLimits(1, self.calDAC2Q_m[vfat]*(256)+self.calDAC2Q_b[vfat], self.calDAC2Q_m[vfat]*(128)+self.calDAC2Q_b[vfat])
                        fitTF1.SetParLimits(2, -0.01, self.Nev[vfat][ch])
                    else:
                        fitTF1.SetParLimits(0, -0.01, self.calDAC2Q_m[vfat]*(256)+self.calDAC2Q_b[vfat])
                        fitTF1.SetParLimits(1, 0.0,  self.calDAC2Q_m[vfat]*(128)+self.calDAC2Q_b[vfat])
                        fitTF1.SetParLimits(2, -0.01, self.Nev[vfat][ch])
                        pass

                    fitTF1.SetParLimits(3, 0.75*init_guess_p3, 1.25*init_guess_p3)
                    
                    if debug:
                        if self.isVFAT3:
                            print "| %i | %i | %i | %i | %f | %f | %f | %f | %f | %f | %f | %f | %f |"%(
                                        stepN,
                                        vfat,
                                        ch,
                                        self.isVFAT3,
                                        self.calDAC2Q_m[vfat]*(256)+self.calDAC2Q_b[vfat],
                                        init_guess_p0,
                                        self.calDAC2Q_m[vfat]*(1)+self.calDAC2Q_b[vfat],
                                        self.calDAC2Q_m[vfat]*(256)+self.calDAC2Q_b[vfat],
                                        init_guess_p1,
                                        self.calDAC2Q_m[vfat]*(128)+self.calDAC2Q_b[vfat],
                                        -0.01,
                                        init_guess_p2,
                                        self.Nev[vfat][ch]
                                    )
                        else:
                            print "| %i | %i | %i | %i | %f | %f | %f | %f | %f | %f | %f | %f | %f |"%(
                                        stepN,
                                        vfat,
                                        ch,
                                        self.isVFAT3,
                                        -0.01,
                                        init_guess_p0,
                                        self.calDAC2Q_m[vfat]*(256)+self.calDAC2Q_b[vfat],
                                        0.0,
                                        init_guess_p1,
                                        self.calDAC2Q_m[vfat]*(128)+self.calDAC2Q_b[vfat],
                                        -0.01,
                                        init_guess_p2,
                                        self.Nev[vfat][ch]
                                    )

                    # Fit
                    fitResult = self.scanHistos[vfat][ch].Fit('myERF','SQ')
                    fitEmpty = fitResult.IsEmpty()
                    if fitEmpty:
                        fitTF1.SetLineColor(kOrange-2)
                        # Don't try to fit empty data again
                        break
                    fitValid = fitResult.IsValid()
                    if not fitValid:
                        continue
                    fitChi2 = fitTF1.GetChisquare()
                    fitNDF = fitTF1.GetNDF()
                    stepN +=1
                    if (fitChi2 < MinChi2Temp and fitChi2 > 0.0):
                        self.scanFuncs[vfat][ch] = fitTF1.Clone('scurveFit_vfat%i_chan%i_h'%(vfat,ch))
                        self.scanFuncs[vfat][ch].SetLineColor(r.kBlue-2)
                        self.scanFitResults[0][vfat][ch] = fitTF1.GetParameter(0)
                        self.scanFitResults[1][vfat][ch] = fitTF1.GetParameter(1)
                        self.scanFitResults[2][vfat][ch] = fitTF1.GetParameter(2)
                        self.scanFitResults[3][vfat][ch] = fitChi2
                        self.scanFitResults[4][vfat][ch] = self.scanCount[vfat][ch]
                        self.scanFitResults[5][vfat][ch] = fitNDF
                        self.fitValid[vfat][ch] = True
                        MinChi2Temp = fitChi2
                        pass
                    if (MinChi2Temp < 50): break
                    pass
                if debug:
                    print("Converged fit results:")
                    print "| stepN | vfatN | vfatCH | isVFAT3 | p0 | p1 | p2 | Chi2 | NDF | NormChi2"
                    print "| ----- | ----- | ------ | ------- | -- | -- | -- | Chi2 | NDF | NormChi2"
                    print "| %i | %i | %i | %i | %f | %f | %f | %f | %i | %f |"%(
                            stepN,
                            vfat,
                            ch,
                            self.isVFAT3,
                            self.scanFitResults[0][vfat][ch],
                            self.scanFitResults[1][vfat][ch],
                            self.scanFitResults[2][vfat][ch],
                            self.scanFitResults[3][vfat][ch],
                            self.scanFitResults[5][vfat][ch],
                            self.scanFitResults[3][vfat][ch] / self.scanFitResults[5][vfat][ch])
                    pass
                pass
            pass
        return self.scanFitResults
    
    def getFunc(self, vfat, ch):
        return self.scanFuncs[vfat][ch]

    def readFile(self, treeFileName):
        inF = r.TFile(treeFileName)
        for event in inF.scurveTree :
            self.feed(event)
        return

def fitScanData(treeFileName, isVFAT3=False, calFileName=None):
    from gempython.gemplotting.utils.anautilities import parseCalFile
    
    # Get the fitter
    if calFileName is not None:
        tuple_calInfo = parseCalFile(calFileName)
        fitter = ScanDataFitter(
                calDAC2Q_m = tuple_calInfo[0],
                calDAC2Q_b = tuple_calInfo[1],
                isVFAT3=isVFAT3
                )
    else:
        fitter = ScanDataFitter(isVFAT3=isVFAT3)
        pass

    # Read the output data
    fitter.readFile(treeFileName)

    # Fit
    return fitter.fit()
