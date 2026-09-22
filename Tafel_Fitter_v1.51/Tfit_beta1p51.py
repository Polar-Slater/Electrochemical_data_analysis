#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 12:08:34 2019

@author: pcagbo
"""

#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import scipy.stats, numpy as np
import matplotlib.pyplot as plt; import os
import pandas as pd; import glob
from Tafel_plot_user_v1p1 import plot_h
from common import indexer, extract_filename, approx_index


currentdir = os.getcwd(); direc = currentdir + '\\Input_files\\*.csv'; files = np.sort(glob.glob(direc))

#Global Variables
R = 8.3145 #J/mol.K
F = 96485 #C/mol
T = 293 #K
n = 1

"""Main call procedure; performs recursive fits, saves all data, and produces final plots of fit dataset.
Test call: Tfit_plot(files[2], 1, 0, 1, [0.01, 0.05], 0.001, [0.900, 1.000], 0.001, 1)"""
def Tfit_plot(filename, header, excelsheet, n, interval, delta_interval, rbound, delta_rbound, binning):
    saveto = extract_filename(filename)[2]
    os.makedirs(os.path.dirname(currentdir + '\\Fits\\' + saveto + '_n=' + str(n) + '\\'))
    os.makedirs(os.path.dirname(currentdir + '\\Fits\\' + saveto + '_n=' + str(n) + '\\Binned\\'))
    data = Vary_param_fit(filename, header, excelsheet, n, interval, delta_interval, rbound, delta_rbound)
    plot_h(data, 3, 2, binning, (saveto + '_n=' + str(n)) )

#Call procedure for recursively performing tafel fits by automatically varying R2 and overpotential widths.
def Vary_param_fit(filename, header, excelsheet, n, interval, delta_interval, rbound, delta_rbound):
    V_int = np.arange(interval[0], interval[1], delta_interval)
    R2_int = np.arange(rbound[0], rbound[1], delta_rbound)
    fitcounts = 0; recursions = 0
    figs_of_merit = np.zeros((len(V_int)*len(R2_int), 9)); counter = 0
    for R2 in R2_int:
        for dV in V_int:
            x = Fit(filename, header, excelsheet, dV, R2, n)
            if type(x[0]) == int:
                recursions += x[1]
            else:
                #value of var x is the return value of fit_engine:
                scantype = x[-1]
                fit_index = x[0][12]; residual = x[0][0][fit_index]; fit_start = x[0][1][0]; slope = x[0][9][fit_index]; io = x[0][2]; R2_tafel = x[0][10][fit_index]; R2_LSV = x[0][11][fit_index]
                if scantype == 'cathodic':
                    figs_of_merit[counter, :] = R2, dV, slope, io, residual, fit_start, R2_tafel, R2_LSV, (fit_start - dV)
                else:
                    figs_of_merit[counter, :] = R2, dV, slope, io, residual, fit_start, R2_tafel, R2_LSV, (fit_start + dV)
                fitcounts += x[3]; recursions += x[3]
            print 'For minimum R2 = ' + str(R2) + ', voltage interval width = ' + str(dV) +'\n'
            counter += 1
    saveto = extract_filename(filename)[2]
    print 'Total number of compliant fits: ' + str(fitcounts)
    print 'Total number of fit conditions tested (# of program recursions): ' + str(recursions)
    #cleaning out [0] row vectors from array (conditions yielding no possible fits); re-initialize counter:
    if np.zeros((1,9)) in figs_of_merit:
        counter = 0
        for every in figs_of_merit:
            if np.array_equal(every, np.zeros((1, 9))[0]):
                figs_of_merit = np.delete(figs_of_merit, counter, 0)
            else:
                counter += 1
    else:
        pass
    dataframe = pd.DataFrame(figs_of_merit, columns = ['R2 threshold', 'Overpotential Fit Width / V', 'Tafel slope / mV Decade-1', 'Exchange Current / A', 'Optimal Residual', 'Starting Fit Potential / V', 'Tafel R2', 'LSV R2', 'Ending Fit Potential'])
    dataframe.to_csv(currentdir + '\\Fits\\' + saveto + '_n=' + str(n) + '\\' + saveto + '_minimized_residues.csv')
    #adjust the output array to match the array dimension for the Tafel_plot procedures
    figs_of_merit2 = np.zeros((len(figs_of_merit), 10)); figs_of_merit2[:,1:] = figs_of_merit
    return figs_of_merit2

def Fit(filename, header, excelsheet, interval, rbound, n):
    #importing data:
    data = np.loadtxt(filename, skiprows = header, delimiter = ',')
    if data[:,0][-1] < 0: #if data is cathodic:
        data = data[data[:,0].argsort()][::-1] #monotonically sort data in descending order by voltage (for cathode data).
        scantype = 'cathodic'
    else:
        data = data[data[:,0].argsort()] #monotonically sort data in ascending order by voltage (for anode data).
        scantype = 'anodic'
    voltage = data[:,0]; lsv = data[:,1]; tafel = data[:,2]

    saveto = extract_filename(filename)[2]
    x = fit_engine(voltage, tafel, lsv, interval, rbound, n)
    if type(x) == int:
       print 'No fit possible for these constraints.'
       fitcount = fit_engine(voltage, tafel, lsv, interval, rbound, n)
       return x, fitcount
    else:
        #performing calculations, saving to dataframe
        dataframe2 = x[8]; fit_index = x[12]; fitcount = x[-1]
        x1 = approx_index(x[1][0], voltage)[0][0]; xn = approx_index(x[1][-1], voltage)[0][0]
        m = x[9][fit_index]; b = x[2]
        chart = np.zeros((1,4)); chart[0,0] = x[1][0]; chart[0,1] = x[1][1]; chart[0,2] = b; chart[0,3] = m
        dataframe = pd.DataFrame(chart, columns = ['Bound 1 (V)', 'Bound 2 (V)', 'Exchange Current', 'Tafel Slope'])
        dataframe.to_csv(currentdir + '\\Fits\\' + saveto + '_n=' + str(n) + '\\' + saveto + '_int=' + str(interval) +'V_' + 'R2='+ str(rbound) + '_n=' + str(n) + '_Fit_Summary.csv')
        dataframe2.to_csv(currentdir + '\\Fits\\' + saveto + '_n=' + str(n) + '\\' + saveto + '_int=' + str(interval) +'V_' + 'R2='+ str(rbound) + '_n=' + str(n) + '_Fit_Results.csv')
        print
        print 'Voltage cutoff = ' + str(voltage[x[7]]) + ' V'
        print 'Fit Interval / V\t', 'Exchange Current / A\t', 'Tafel slope (mV/decade)\t', 'Tafel Residue'
        print str(x[1]), '\t', str(b), '\t', str(m), '\t', x[0][fit_index]
        print
        print 'Actual Tafel R2: \t' + str(x[10][fit_index]) + ' ; Actual LSV R2: \t' + str(x[11][fit_index])    
        #Plot as four axes, returned as a 2-d array
        plt.subplot(2, 2, 1)
        plt.plot(voltage, tafel, 'ko-')
        plt.plot(voltage[x1 : xn], tafel[x1 : xn],'wo')
        if voltage[-1] > 0: #if fitting anodic data, otherwise:
            xlow = voltage[x1]; xhigh = voltage[xn]
        else:
            xlow = voltage[xn]; xhigh = voltage[x1]
        v = np.arange(xlow, xhigh, abs(xlow - xhigh) / 10)
        plt.plot(v, (1000/m)*v + np.log10(b), 'r-', linewidth = 2.0)
        plt.title('Tafel Fit')
        #plt.xlabel('Overpotential / V')
        plt.ylabel('log i')
        plt.grid(False)
    
        plt.subplot(2, 2, 3)
        plt.plot(voltage, lsv, 'k-')
        plt.title('LSV')
        plt.xlabel('Overpotential / V')
        plt.ylabel('Current (i) / Amps')
        plt.grid(False)
        plt.subplot(2, 2, 2)
        plt.plot(x[3], x[0], 'ro')
        plt.title('Tafel Residue')
        plt.ylabel('Residual (|i$_0$nF/RT - di/dV|)')
        plt.xlabel('Starting Potential value (V$_i$) for interval [V$_i$, V$_i$ + dV])')
        plt.grid(False)

        plt.subplot(2, 2, 4)
        plt.plot(x[4], x[5], 'ko') #differential LSV
        plt.plot(x[4], x[6], 'r-') #polynomial fit to derivative LSV
        plt.title('Differential LSV')
        plt.xlabel('Overpotential / V'); plt.ylabel('di/dV')
        plt.grid(False)#; plt.show()
        
        figure = plt.gcf(); figure.set_size_inches(19.2, 10.8)
        plt.tight_layout()
        plt.savefig(currentdir + '\\Fits\\' + saveto + '_n=' + str(n) + '\\' + saveto + '_int=' + str(interval)+'V_' + 'R2='+ str(rbound) + '_n=' + str(n) + '_PLOTS.png')
        plt.clf()
        return [x, m, b, fitcount, scantype]

def fit_engine(voltage, ytafel, ylsv, interval, rbound, n):
    #compute derivative LSV:
    dx, dy = np.array( (derivative(voltage, ylsv)) ) #; dy = abs(dy)
    #perform least-squares fit of derivative LSV, find function's maximum:
    dfit = np.poly1d(np.polyfit(dx, dy, 15)); p = np.poly1d(dfit)
    fitlist = []
    for every in dx:
        fitlist.append(p(every))
    inflection = indexer(max(fitlist), fitlist)[0][0] 
    if bool(inflection):
        #fit using values below the dlsv maximum (before the onset of diffusion effects)
        #truncating data to exclude values below dlsv maximum:
        voltage_sub = voltage[:inflection]; ytafel_sub = ytafel[:inflection]; ylsv_sub = ylsv[:inflection]
    else: 
        voltage_sub = voltage; ytafel_sub = ytafel; ylsv_sub = ylsv
        inflection = None
    
    counter = 0
    lst = [ [],[],[],[],[],[] ]; taf_slopes = []
    if voltage_sub[-1] > 0:#Condition for anode data.
        while voltage_sub[counter] + interval < voltage_sub[-1]: 
            index = approx_index(voltage_sub[counter]+interval, voltage_sub)[0][0]
            # stats.lingress output: [ slope, intercept, r, p_value, std_error ]
            test1 = scipy.stats.linregress(voltage_sub[counter : counter + index], ytafel_sub[counter : counter + index])
            test2 = scipy.stats.linregress(voltage_sub[counter : counter + index], ylsv_sub[counter : counter + index])
            # Test regions for linearity:
            dlogjdV = 1000/(test1[0]); J0 = 10**( test1[1] ); djdV = abs( test2[0] )  
            #JO = y-intercept of Tafel regression, djdV = slope of LSV regression, dlogJ/dV = slope of Tafel regression
            R2_Tafel = test1[2]**2; R2_LSV = test2[2]**2
            if R2_Tafel >= rbound and R2_LSV >= rbound: #if R2 correlation is at least greater than some threshold for linearity (rbound):
                lst[0].append(J0) #exchange currents
                lst[1].append([djdV, voltage_sub[counter]]) #differentials and associated potentials
                lst[2].append(J0*F/(n*R*T))
                lst[3].append([voltage_sub[counter], djdV - J0*F/(n*R*T)]) #differentials and associated potentials
                lst[4].append(R2_Tafel); lst[5].append(R2_LSV)
                taf_slopes.append(dlogjdV)
            else:
                pass
            counter += 1
    else: #Otherwise, treat data as cathodic.
        while voltage_sub[counter] - interval > voltage_sub[-1]: #Condition for cathode data
            index = approx_index(voltage_sub[counter]-interval, voltage_sub)[0][0]
            # stats.lingress output: [ slope, intercept, r, p_value, std_error ]
            test1 = scipy.stats.linregress(voltage_sub[counter : counter + index], ytafel_sub[counter : counter + index])
            test2 = scipy.stats.linregress(voltage_sub[counter : counter + index], ylsv_sub[counter : counter + index])
            # Test regions for linearity:
            dlogjdV = 1000/(test1[0]); J0 = 10**( test1[1] ); djdV = abs( test2[0] )  
            #JO = y-intercept of Tafel regression, djdV = slope of LSV regression, dlogJ/dV = slope of Tafel regression
            R2_Tafel = test1[2]**2; R2_LSV = test2[2]**2
            if R2_Tafel >= rbound and R2_LSV >= rbound: #if R2 correlation is at least greater than some threshold for linearity (rbound):
                lst[0].append(J0) #exchange currents
                lst[1].append([djdV, voltage_sub[counter]]) #differentials and associated potentials
                lst[2].append(J0*F/(n*R*T))
                lst[3].append([voltage_sub[counter], djdV - J0*F/(n*R*T)]) #differentials and associated potentials
                lst[4].append(R2_Tafel); lst[5].append(R2_LSV)
                taf_slopes.append(dlogjdV)
            else:
                pass
            counter += 1

    #manage lists:
    lst1_slopes, lst1_voltages = [], []
    for every in lst[1]:
        lst1_slopes.append(every[0]) ; lst1_voltages.append(every[1])

    #extract potential range for fitting & Tafel parameters.
    residue = abs(np.array(lst1_slopes) - np.array(lst[2]))
    if len(residue) > 0:
        residue_index = approx_index(min(residue), residue)[0][0] #finding list index for lowest residue (J0*F/RT - dJ/dV)
        if voltage_sub[-1] > 0:
            fit_range = [lst1_voltages[residue_index], lst1_voltages[residue_index] + interval]
        else:
            fit_range = [lst1_voltages[residue_index], lst1_voltages[residue_index] - interval]  
        exchange_rate = lst[0][residue_index] #return the JO from the ideal fit
        chart = np.zeros([len(lst[0]), 7])
        chart[:,0] = lst1_voltages; chart[:,1] = lst[0]; chart[:,2] = lst1_slopes; chart[:,3] = residue
        chart[:,4] = lst[4]; chart[:,5] = lst[5]; chart[:,6] = taf_slopes
        dataframe = pd.DataFrame(chart, columns = ['Starting Potentials', 'J0', 'dJ/dV', 'Residue (|J0*F/RT-dJ/dV|)', 'Tafel R^2', 'LSV R^2', 'Tafel Slope / mV decade-1'])
        return residue, fit_range, exchange_rate, lst1_voltages, dx, dy, fitlist, inflection, dataframe, taf_slopes, lst[4], lst[5], residue_index, counter 
    else:
        return counter

#use to perform quick visual checks of differential LSV data prior to fitting;
def check_difflsv(filename):
    if filename[-3:] =='csv':
        header = input('provide first line of data to remove headers: ')
        data = np.loadtxt(filename, skiprows = header, delimiter = ',')
        voltage = data[:,0]; lsv = data[:,1]
    else:
        print 'Invalid file format provided. Use .csv files only'
        file = input('Filename of dataset: ')
        print
        check_difflsv(file)
    dx, dy = derivative(voltage, lsv)
    plt.plot(dx, dy, 'bo'); plt.show()

#Calculate function derivative numerically.
def derivative(xlist, ylist):
    z = 1; dxlist = []; dydxlist = []
    while z < len(xlist):
         dx = xlist[z] - xlist[z - 1]; xbar = 0.5*(xlist[z] + xlist[z -1])
         dy = ylist[z] - ylist[z - 1]; diff = dy / dx
         dxlist.append(xbar); dydxlist.append(diff)
         z += 1
    return dxlist, dydxlist
   
"""General, user-friendly call procedure; interactive prompts; .csv files only.
interval is a list of low and high overpotential widths to use for fitting (i.e, interval = [low, high]).
rbound is a list of the same form as interval for low and high R2 values to fit over
delta_* variables are integer or float values controlling the increment variation of their respective parameters."""
def Run():
    print 'Files to be analyzed must be in the current working directory.'
    #filedir = os.getcwd() + '/*.csv'; files = np.sort(glob.glob(filedir))
    files = np.sort(glob.glob(direc))
    counter = 0
    print 'File number\t', 'Filename'
    for each in files:
        print counter, '\t', each
        counter += 1
        
    f = input('Which dataset do you want to inspect (enter file number)? ') 
    if files[f][-4:] == '.csv':
        header = input('Enter the last line of the file header (enter "0" if none present): ')
        fit_order = input('Fit dLSV with a polynomial of order n = 1,2,3..? ')
        data = np.loadtxt(files[f], skiprows = header, delimiter = ',')
        voltage = data[:,0]; lsv = data[:,1]
        dx, dy = derivative(voltage, lsv)
        #perform least-squares fit of derivative LSV, find function's maximum:
        dfit = np.poly1d(np.polyfit(dx, dy, fit_order)); p = np.poly1d(dfit)
        fitlist = []
        for every in dx:
            fitlist.append(p(every))
        inflection = indexer(max(fitlist), fitlist)[0][0]
        plt.subplot(2,1,1)
        plt.plot(dx, dy, 'ko'); plt.plot(dx, fitlist, 'c', linewidth = 2.0)
        plt.axvline(x = dx[inflection], linewidth = 1.5, linestyle = '--', color = 'r')
        plt.ylabel('dI/dV'); plt.grid(False)
        plt.subplot(2,1,2)
        plt.plot(voltage, lsv, 'k', linewidth = 2.0)
        plt.axvline(x = dx[inflection], linewidth = 1.5, linestyle = '--', color = 'r')
        plt.xlabel('Overpotential / V')
        plt.ylabel('I / Amps'); plt.grid(False)
        figure = plt.gcf(); figure.set_size_inches(9.6, 5.4)
        plt.tight_layout(); plt.show()
        print 'voltage cutoff (blue dotted line) = ' + str(voltage[inflection]) + ' V'
        accept = raw_input('do you want to accept this fit (y/n)? ')
        if accept == 'Y' or 'y':
            interval = input('Enter the range of overpotential window sizes (dV) to check, in volts (i.e., [0.01, 0.05] ): ')
            delta_interval = input('Enter the dV increment to use, in volts (i.e., 0.001): ')
            rbound = input('Enter the range of R-squared values over which to conduct the fits (i.e., [0.900, 1.000] ): ')
            delta_rbound = input('Enter the increment for the R-squared value range (i.e., 0.001): ' )
            binning = input('Enter the binning size to use for dV-span optimization, in millivolts (1 mV default): ')
            Tfit_plot(files[f], header, 0, 1, interval, delta_interval, rbound, delta_rbound, binning)
        else:
            Run()
    else:
        print 'Input files must be in .csv format.'
