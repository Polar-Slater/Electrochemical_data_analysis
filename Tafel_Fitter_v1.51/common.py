#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 26 13:32:38 2019

@author: pcagbo
"""
def indexer(value, list):
    index = 0
    indices = []; listvalues = []
    if value in list:
        while (index + 1) <= len(list):
            if value == list[index]:
                indices.append(index); listvalues.append(list[index])
            index += 1
        return indices, listvalues
    return 'no such value in list'

def extract_filename(path):
    counter = -1
    if '\\' in path:
        while -counter < len(path):
            if path[counter] == '\\':
                dir = path[:counter+1]
                file = path[counter+1:]; filename = file[:-4]; extension = file[-4:]
                return [dir, file, filename, extension]
            else:
                counter -= 1
    else:
        return path

def approx_index(value, list):
    residual = []
    if value == None or value in list:
        return indexer(value, list)
    else:
        #make vector of the form [X1-value, X2-value,..., Xn-value...]
        #find index of min value of vector (location of the number closest to value)
        for every in list:
            residual.append(abs(value - every))
        return indexer( min(residual), residual)
