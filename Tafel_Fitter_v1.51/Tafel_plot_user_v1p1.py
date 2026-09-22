#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 24 10:53:41 2019

@author: pcagbo
"""

from scipy.interpolate import griddata
from scipy import stats; import pandas as pd
import numpy as np; import matplotlib.pyplot as mt
import glob; import os
from common import indexer, extract_filename

mt.rcParams.update({'font.size': 20, 'lines.markersize': 15})
currentdir = os.getcwd()

#Test dataset
files = np.sort(glob.glob('/home/pcagbo/Desktop/Tafel/Test_datasets/*.csv'))
resfiles = np.sort(glob.glob('/home/pcagbo/Desktop/Tafel/min_residues/*.csv'))

def plot(filename, xcol_index, ycol_index, binning):
    array = np.loadtxt(filename, skiprows = 1, delimiter = ',')
    file0 = extract_filename(filename)[2]
    os.makedirs(os.path.dirname(currentdir + '\\Fits\\' + file0 + '\\Binned\\'))
    plot_h(array, xcol_index, ycol_index, binning, file0)

def plot_batch(filenames, xcol_index, ycol_index, binning):
    for every in filenames:
        array = np.loadtxt(every, skiprows = 1, delimiter = ',')
        file0 = extract_filename(every)[2]
        os.makedirs(os.path.dirname(currentdir + '\\Fits\\' + file0 + '\\Binned\\'))
        for each in binning:
            plot_h(array, xcol_index, ycol_index, each, file0)

def plot_h(array, xcol_index, ycol_index, interval, file0):
    #cleaning out [0] row vectors from array (conditions yielding no possible fits); re-initialize counter:
    if np.zeros((1,9)) in array[:,1:]:
        counter = 0
        for every in array:
            if np.array_equal(every[1:], np.zeros((1, 9))[0]):
                array = np.delete(array, counter, 0)
            else:
                counter += 1
    else:
        pass
    #Extracting binned dataset from input array:
    binned_data = binner(array, xcol_index, ycol_index, interval)
    binned, binnedR2s, fullarray = binned_data[1:4]
    print 'Binned Array of dV-Optimized Tafel Values:'
    dataframe1 = pd.DataFrame(binned, columns = ['Tafel Bin / mV decade-1', 'R2 threshold', 'Overpotential Width / V', 'Tafel slope / mV Decade-1', 'Exchange Current / A', 'Optimal Residual', 'Starting Fit Overpotential / V', 'Tafel R2', 'LSV R2', 'Ending Fit Potential'])
    print dataframe1
    print 'dV+R2-optimized Fits:'
    dataframe2 = pd.DataFrame(binnedR2s, columns = ['Tafel Bin / mV decade-1', 'R2 threshold', 'Overpotential Width / V', 'Tafel slope / mV Decade-1', 'Exchange Current / A', 'Optimal Residual', 'Starting Fit Overpotential / V', 'Tafel R2', 'LSV R2', 'Ending Fit Potential'])
    print dataframe2

    #Display the potential range of Residue-optimized fits:
    mt.subplot(2, 3, 1) #2d histogram of (dV, Tafel slope, Z=counts)
    mt.hist2d(array[:,3], abs(array[:,2]), bins = 70, cmap = 'nipy_spectral_r'); mt.colorbar(label = 'Counts')
    mt.xlabel('Tafel Slope / mV decade$^-$$^1$'); mt.ylabel('Overpotential Fit Width / V')

    #Display the range of Tafel slopes spanning the set of Residue-minimized fits, and the slope displaying the highest
    #degree of interval convergence (same slope across the widest range of fit widths):
    mt.subplot(2, 3, 2) #2d histogram of (R2, Tafel slope, Z=counts)
    mt.hist2d(array[:,3], array[:,7], bins = 70, cmap = 'nipy_spectral_r'); mt.colorbar(label = 'Counts')
    mt.xlabel('Tafel Slope / mV decade$^-$$^1$'); mt.ylabel('Tafel Fit R$^2$')

    #Display the range of Tafel slopes vs Starting Voltage of linear fit.
    mt.subplot(2, 3, 3) #2d histogram of (Tafel Slope, Starting Fit Voltage, Z=counts)
    mt.hist2d(array[:,3], array[:,6], bins = 70, cmap = 'nipy_spectral_r'); mt.colorbar(label = 'Counts')
    mt.xlabel('Tafel Slope / mV decade$^-$$^1$'); mt.ylabel('Starting Fit Overpotential / V')

    #Plot of Binned dataset (x,y) = (Tafel slope bin, dV)
    mt.subplot(2, 3, 4)
    mt.plot(binned[:,0], abs(binned[:,2]), 'co') #optimal dV-binned fits
    mt.plot(binnedR2s[:,0], abs(binnedR2s[:,2]), 'ro') #optimal dV, R2-binned fit(s)
    mt.plot(fullarray[:,0], abs(fullarray[:,2]), 'k+') #full array data, binned
    mt.xlabel('Tafel Slope Bin / mV decade$^-$$^1$'); mt.ylabel('Overpotential Fit Width / V')    
    
    #Plot of Binned dataset (x,y) = (Tafel slope bin, R2)
    mt.subplot(2, 3, 5)
    mt.plot(binned[:,0], binned[:,7], 'co') #optimal dV-binned fits
    mt.plot(binnedR2s[:,0], binnedR2s[:,7], 'ro') #optimal dV, R2-binned fit(s)
    mt.plot(fullarray[:,0], fullarray[:,7], 'k+') #full array data, binned
    mt.xlabel('Tafel Slope Bin / mV decade$^-$$^1$'); mt.ylabel('Tafel Fit R$^2$')
    
    #Scatter plot of all fits yielding dV and R2-optimized Tafel slopes.
    mt.subplot(2, 3, 6)
    #1. Generate contour map:
    #x = array[:,6]; y = array[:,2] + array[:,6]; z = array[:,3] #generate contours using individual Tafel slopes.
    levels = np.linspace(min(array[:,3]), max(array[:,3]), 100)
    x = array[:,6]; y = array[:,9]; z = array[:,3] #generate contours using Tafel slope bins.
    X,Y = np.meshgrid(x,y); Z = griddata((x,y), z, (X,Y), method = 'nearest')
    mt.contourf(X,Y,Z, levels); mt.colorbar(label = 'Tafel Slope / mV decade$^-$$^1$')
    #2. Generate scatter plot:
    mt.plot(array[:,6], array[:,9], 'k+') #plot all fits.
    mt.plot(binned[:,6], binned[:,9], 'co') #plot dV-optimized Tafel fits (spanning widest range of dVs).
    mt.plot(binnedR2s[:,6], binnedR2s[:,9], 'ro')# plot dV+R2-optimimzed fits (highest R2s).
    mt.xlabel('Starting Fit Overpotential / V'); mt.ylabel('Ending Fit Overpotential / V')#; mt.title('Voltage Ranges for Tafel Slope = m')

    figure = mt.gcf(); figure.set_size_inches(19.2, 10.8)
    mt.tight_layout()
    dataframe1.to_csv(currentdir + '\\Fits\\' + file0 + '\\Binned\\' + file0 + '_dV_optimization_binning='+ str(interval) + '_mV.csv')
    dataframe2.to_csv(currentdir + '\\Fits\\' + file0 + '\\Binned\\' + file0 + '_dV+R2_optimization_binning='+ str(interval) + '_mV.csv')
    mt.savefig(currentdir + '\\Fits\\' + file0 + '\\Binned\\' + file0 + '_dV+R2_PLOTS_binning='+str(interval) + '_mV.png', dpi = 50)
    mt.show()

#Calculates a binning value given a desired interval width.
def calc_bin(low, high, interval):
    return (high - low) / interval

#Bin data from a file (.csv/.txt spreadsheet).
def bin_file(filename, xcol_index, ycol_index, interval):
    array = np.loadtxt(filename, skiprows = 1, delimiter = ',')
    return binner(array, xcol_index, ycol_index, interval)

#Binning function.
def binner(array, xcol_index, ycol_index, interval): 
    array = array[array[:,xcol_index].argsort()] #sort array monotonically by Tafel slope (x) column.
    x_array = array[:, xcol_index]; y_array = array[:, ycol_index]
    bincount = calc_bin(min(x_array), max(x_array), interval)
    #Generated output of stats.binned_statistic(): value of given statistic in each bin; bin edges; bin index.
    bin_edges = stats.binned_statistic(x_array, y_array, bins=bincount)[1]
    #assign each row (fit) in array to its proper Tafel bin.
    bin_index = np.digitize(x_array, bin_edges, right = True) #np.digitize: returns index of the bin in bin_edges to which a value in x_array belongs.
    bin_value = []
    for every in bin_index:
        bin_value.append(bin_edges[every])
    array[:,0] = bin_value
    
    #return the first index of each unique bin value in "array":
    unique, first_index = np.unique(array[:,0], return_index = True)
    
    #Find the bin(s) with the highest number of unique voltage widths (unique dVs); generates a list.
    unique_dVs = np.zeros((len(first_index),3)); counter = 0 
    unique_dVs[:,0] = first_index
    while counter + 1 < len(first_index):
        unique_dVs[counter,1] = len(np.unique(array[ first_index[counter]:first_index[counter+1], 2] ) )
        counter += 1
    if counter + 1 == len(first_index): #Account for data in the last bin:
        unique_dVs[counter,1] = len(np.unique(array[ first_index[counter]:, 2] ) )
    
    #calculate the total number of members in each bin:
    counter = 0
    while counter + 1 < len(unique_dVs):
        unique_dVs[counter,2] = unique_dVs[counter+1,0] - unique_dVs[counter,0]
        counter += 1
    if counter + 1 == len(unique_dVs):
        unique_dVs[counter,2] = (len(array)-1) - unique_dVs[counter,0]
    mostdVs = indexer(max(unique_dVs[:,1]), unique_dVs[:,1])[0] #list of the starting indices of the widest-spanning Tafel bins.
    
    #Find required length for binned array:
    l = 0
    for every in mostdVs:
        l += unique_dVs[int(every),2]
    #Find the fits of Tafel binning values spanning the highest number of dVs.
    binned = np.zeros((int(l), 10)); counter = 0
    for every in mostdVs:
        #find indices of unique dV values in each Tafel bin
        array_index = unique_dVs[int(every),0] ; binsize = unique_dVs[int(every),2]
        binned[counter:int(counter + binsize),:] = array[int(array_index):int(array_index + binsize),:]
        counter += int(binsize)
    
    #Find the fits with the maximal R2 in the Tafel bin.
    maxR2s = indexer(max(binned[:,7]), binned[:,7])[0]
    binnedR2s = np.zeros((len(maxR2s), 10)); counter = 0
    for every in maxR2s:
        array_index = maxR2s[counter]
        binnedR2s[counter,:] = binned[array_index,:]
        counter += 1
    return l, binned, binnedR2s, array, mostdVs, unique_dVs, maxR2s  #bin value of the optimum fit

def Plot_fit():
    print 'Use this for plotting the residue-minimized datasets generated through fitting (*minimized_residues.csv).'
    print 'Files to be analyzed must be in the current working directory.'
    filedir = os.getcwd() + '\\*.csv'; optimizations = np.sort(glob.glob(filedir))
    counter = 0
    print 'File number\t', 'Filename'
    for each in optimizations:
        print counter, '\t', each
        counter += 1
    f = input('Which residue-optimized dataset do you want to inspect (enter file number)?: ')
    bin_val = input('Enter a binning value for these data (1 mV/decade is typical): ')
    plot(optimizations[f], 3,2, bin_val)

def batch_plot(path):
    files = glob.glob(path)
    for every in files:
        plot(every)
