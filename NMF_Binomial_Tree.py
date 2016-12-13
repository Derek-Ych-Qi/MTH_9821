from __future__ import division
import numpy as np
from Option import *
from NMF_Black_Scholes import *
import copy
import matplotlib as plt

class BinomialTree:
    def __init__(self, N, r, Op):
        '''
        Generates the binomial tree framework for a certain option
        :param N: Time steps
        :param r: risk free interest rate in units
        :param Op: An Option class instance
        '''
        self.tstep = N
        self.riskfree = r
        dt = Op.maturity / N
        self.u = np.exp(Op.vol * np.sqrt(dt))
        self.d = 1 / self.u
        self.p = (np.exp((r - Op.div_rate) * dt) - self.d) / (self.u - self.d)

    def finalvalue(self, Op):
        '''
        Generates the final state value of an option with a N step binomial tree model
        :return: a [N + 1, 1] vector containing the final values
        '''
        N, u, d = self.tstep, self.u, self.d
        fv = np.zeros([N + 1, 1])
        fs = np.zeros([N + 1, 1])
        fs[0] = u ** N * Op.spot
        fv[0] = Op.value(fs[0])
        for i in xrange(1, N + 1):
            fs[i] = fs[i - 1] * d / u
            fv[i] = Op.value(fs[i])
        return fv    


def Binomial_Tree_Pricing(Op, BMT, Greek = False):
    '''
    Calculate the risk neutral price of a certain option with general Binomial Tree model.
    :param Op: An instance from class Option
    :param BMT: An binomial tree instance with step N, rate r, upfactor u and downfactor d
    :return: The risk-neutral binomial tree price (by taking risk neutral expectation)
    '''
    S0, K, T, q = Op.spot, Op.strike, Op.maturity, Op.div_rate
    N, r, u, d, p = BMT.tstep, BMT.riskfree, BMT.u, BMT.d, BMT.p
    dt = T / N
    # p = (np.exp((r - q) * dt) - d) / (u - d) # risk neutral probability for the stock price to go up
    fv = BMT.finalvalue(Op)
    for j in xrange(N - 1, -1, -1):
        for i in xrange(0, j + 1):
            if Op.ae == 'EU':
                fv[i] = np.exp(-r * dt) * (p * fv[i] + (1 - p) * fv[i + 1])
            elif Op.ae == 'AM':
                Sc = S0 * u ** (j - i) * d ** i
                if Op.cp == 'C':
                    fv[i] = max(np.exp(-r * dt) * (p * fv[i] + (1 - p) * fv[i + 1]), Sc - K)
                elif Op.cp == 'P':
                    fv[i] = max(np.exp(-r * dt) * (p * fv[i] + (1 - p) * fv[i + 1]), K - Sc)
            elif Op.ae == 'DNO': #Down and Out options
                B = Op.Barrier
                Sc = S0 * u ** (j - i) * d ** i
                if Op.cp == 'C':
                    fv[i] = np.exp(-r * dt) * (p * fv[i] + (1 - p) * fv[i + 1]) * int(Sc > B)
                elif Op.cp == 'P':
                    fv[i] = np.exp(-r * dt) * (p * fv[i] + (1 - p) * fv[i + 1]) * int(Sc > B)
        if j == 2:
            fv2 = [float(fv[0]), float(fv[1]), float(fv[2])]
            fs2 = [S0 * u ** 2, S0 * u * d, S0 * d ** 2]
        if j == 1:
            fv1 = [float(fv[0]), float(fv[1])]
            fs1 = [S0 * u, S0 * d]

    if not Greek:
        return fv[0][0]
    else:
        Delta = (fv1[0] - fv1[1]) / (fs1[0] - fs1[1])
        Gamma = ((fv2[0] - fv2[1]) / (fs2[0] - fs2[1]) - (fv2[1] - fv2[2]) / (fs2[1] - fs2[2])) / ((fs2[0] - fs2[2]) / 2)
        Theta = (fv2[1] - fv[0][0]) / (2 * dt)
        return (fv[0][0], Delta, Gamma, Theta)


def Avg_Binomial_Tree_Pricing(Op, BMT, Greek = False):
    '''
    Calculate the risk neutral price of a certain option with Average Binomial Tree model.
    :param Op: An instance from class Option
    :param BMT: An binomial tree instance with step N, rate r, upfactor u and downfactor d
    :return: The risk-neutral binomial tree price (by taking risk neutral expectation)
    '''
    BMT_1 = BinomialTree(BMT.tstep + 1, BMT.riskfree, Op)
    if Greek:
        old = Binomial_Tree_Pricing(Op, BMT, Greek)
        new = Binomial_Tree_Pricing(Op, BMT_1, Greek)
        avgbmt_tuple = tuple([(old[i] + new[i]) / 2 for i in range(4)])
        return avgbmt_tuple
    else:
        return (Binomial_Tree_Pricing(Op, BMT) + Binomial_Tree_Pricing(Op, BMT_1)) / 2


def Binomial_Black_Scholes(Op, BMT, Greek = False):
    '''
    Calculate the risk neutral price of a certain option with Binomial Black Scholes model.
    :param Op: An instance from class Option
    :param BMT: An binomial tree instance with step N, rate r, upfactor u and downfactor d
    :param Greek: A boolean variable whether the output should contain greeks
    :return:
    '''
    S0, K, T, q = Op.spot, Op.strike, Op.maturity, Op.div_rate
    N, r, u, d, p = BMT.tstep, BMT.riskfree, BMT.u, BMT.d, BMT.p
    dt = T / N
    # Generate the first step option value using BS formula
    fv = np.zeros([N, 1])
    Op.maturity = dt
    Op.spot = u ** (N - 1) * S0
    fv[0] = Black_Scholes_Pricing(Op, r)
    for i in xrange(1, N):
        Op.spot *= d / u
        if Op.ae == 'EU':
            fv[i] = Black_Scholes_Pricing(Op, r)
        if Op.ae == 'AM':
            if Op.cp == 'C':
                fv[i] = max(Black_Scholes_Pricing(Op, r), Op.spot - K)
            elif Op.cp == 'P':
                fv[i] = max(Black_Scholes_Pricing(Op, r), K - Op.spot)
    # print fv
    for j in xrange(N - 2, -1, -1):
        for i in xrange(0, j + 1):
            if Op.ae == 'EU':
                fv[i] = np.exp(-r * dt) * (p * fv[i] + (1 - p) * fv[i + 1])
            if Op.ae == 'AM':
                 Sc = S0 * u ** (j - i) * d ** i
                 if Op.cp == 'C':
                     fv[i] = max(np.exp(-r * dt) * (p * fv[i] + (1 - p) * fv[i + 1]), Sc - K)
                 elif Op.cp == 'P':
                     fv[i] = max(np.exp(-r * dt) * (p * fv[i] + (1 - p) * fv[i + 1]), K - Sc)
                # fv[i] = np.exp(-r * dt) * (p * fv[i] + (1 - p) * fv[i + 1])
            # if j == 3:
                # print Sc, K, K - Sc

        if j == 2:
            fv2 = [float(fv[0]), float(fv[1]), float(fv[2])]
            fs2 = [S0 * u ** 2, S0 * u * d, S0 * d ** 2]
        if j == 1:
            fv1 = [float(fv[0]), float(fv[1])]
            fs1 = [S0 * u, S0 * d]
        # print fv

    Op.spot = S0
    Op.maturity = T
    if not Greek:
        return fv[0][0]
    else:
        Delta = (fv1[0] - fv1[1]) / (fs1[0] - fs1[1])
        Gamma = ((fv2[0] - fv2[1]) / (fs2[0] - fs2[1]) - (fv2[1] - fv2[2]) / (fs2[1] - fs2[2])) / ((fs2[0] - fs2[2]) / 2)
        Theta = (fv2[1] - fv[0][0]) / (2 * dt)
        return (fv[0][0], Delta, Gamma, Theta)


def Binomial_Black_Scholes_Richardson(Op, BMT, Greek = False):
    '''
    Calculate the risk neutral price of a certain option using Binomial Black Scholes model with Richardson's extrapolation.
    :param Op: An instance from class Option
    :param BMT: An binomial tree instance with step N, rate r, upfactor u and downfactor d
    :return:
    '''
    N, r = BMT.tstep, BMT.riskfree
    BMT_2 = BinomialTree(int(N / 2), r, Op)
    if Greek:
        full = Binomial_Black_Scholes(Op, BMT, Greek)
        half = Binomial_Black_Scholes(Op, BMT_2, Greek)
        pbbsr_tuple = tuple([full[i] * 2 - half[i] for i in range(4)])
        return pbbsr_tuple
    else:
        return Binomial_Black_Scholes(Op, BMT) * 2 - Binomial_Black_Scholes(Op, BMT_2)


if __name__ == "__main__":
    eup = Option(S0 = 41, K = 40, T = 1, q = 0.01, sigma = 0.3, cp = 'P', ae = 'EU')
    amp = Option(S0 = 41, K = 40, T = 1, q = 0.01, sigma = 0.3, cp = 'P', ae = 'AM')
    bmt = BinomialTree(N = 5, r = 0.03, Op = amp)
    # peup = Binomial_Tree_Pricing(eup, bmt)
    # pavgeup = Avg_Binomial_Tree_Pricing(eup, bmt)
    # pbbs = Binomial_Black_Scholes(eup, bmt)
    # pbbsr = Binomial_Black_Scholes_Richardson(eup, bmt)
    # print peup
    # print pavgeup
    # print pbbs
    # print pbbsr
    (peup, deltae, gammae, thetae) = Binomial_Tree_Pricing(eup, bmt, True)
    (pamp, deltaa, gammaa, thetaa) = Binomial_Tree_Pricing(amp, bmt, True)
    print [peup, deltae, gammae, thetae]
    print [pamp, deltaa, gammaa, thetaa]
    # pabt, Deltaabt, Gammaabt, Thetaabt = Avg_Binomial_Tree_Pricing(eup, bmt, True)
    # print pabt, Deltaabt, Gammaabt, Thetaabt
    # pbbs, Deltabbs, Gammabbs, Thetabbs = Binomial_Black_Scholes(amp, bmt, True)
    # print pbbs, Deltabbs, Gammabbs, Thetabbs
    # pbbsr = Binomial_Black_Scholes_Richardson(eup, bmt, False)
    # print pbbsr