"""
SmarterBoard Component Classifier 
author: rlouie 
"""
import cv2

import numpy as np
import matplotlib.pyplot as plt

from skimage import exposure, transform
from skimage.filter import threshold_otsu, gabor_filter

from utils import Utils

class Preprocessing:
    
    @staticmethod
    def binary_from_thresh(img):
        """ Base function for converting to binary using a threshold 
        args:
            img: m x n ndarray
        """
        thresh = threshold_otsu(img)
        binary = img < thresh
        return binary

    @staticmethod
    def binary_from_laplacian(img):
        """ Function that converts an image into binary using
        a laplacian transform and feeding it into binary_from_thresh 
        args:
            img: m x n ndarray
        """
        laplacian = cv2.Laplacian(img,cv2.CV_64F)
        return Preprocessing.binary_from_thresh(laplacian)

    @staticmethod
    def scale_image(img,scaler,org_dim):
        """ resizes an image based on a certain scaler 
        args:
            img: m x n ndarray 
            scaler: int or float. A value of 1.0 would output a image.shape = org_dim
            org_dim: tuple. Denoting (width, height)
        returns: ndarray. Scaled image """
        width, height = org_dim
        output_width = int(scaler*width)
        output_height = int(scaler*height)
        # return transform.resize(img, (output_height, output_width))
        return cv2.resize(img, (output_width, output_height), interpolation=cv2.INTER_CUBIC)

    @staticmethod
    def standardize_shape(img):
        """ standardizes the shape of the images to a tested shape for gabor 
        filters 
        args:
            img: m x n ndarray
        """
        return Preprocessing.scale_image(img, scaler=.25, org_dim=(256,153))
    
    @staticmethod
    def angle_pass_filter(img, frequency, theta, bandwidth):
        """ returns the magnitude of a gabor filter response for a certain angle 
        args:
            img: m x n ndarray
        """
        real, imag = gabor_filter(img, frequency, theta, bandwidth)
        mag = np.sqrt(np.square(real) + np.square(imag))
        return mag
    
    @staticmethod
    def frontslash_filter(img, denom, freq, bandwidth):
        """ intensifies edges that look like a frontslash '/' 
        args:
            img: m x n ndarray
        """
        theta = np.pi*(1.0/denom)
        return Preprocessing.angle_pass_filter(img,freq,theta,bandwidth)
    
    @staticmethod
    def backslash_filter(img,denom,freq,bandwidth):
        """ intensifies edges that look like a backslash '\' 
        args:
            img: m x n ndarray
        """
        theta = np.pi*(-1.0/denom)
        return Preprocessing.angle_pass_filter(img,freq,theta,bandwidth)


class FeatureExtraction:
    
    denom = 4.0
    freq = 0.50
    bw = 0.80
    
    @staticmethod
    def mean_exposure_hist(nbins, *images):
        """ calculates mean histogram of many exposure histograms
        args:
            nbins: number of bins
            *args: must be images (ndarrays) i.e r1, r2
        returns:
            histogram capturing pixel intensities """
        hists = []
        for img in images:
            hist, _ = exposure.histogram(img,nbins)
            hists.append(hist)
        return np.sum(hists, axis=0) / len(images)
    
    @staticmethod
    def mean_exposure_hist_from_gabor(img,nbins):
        frontslash = Preprocessing.frontslash_filter(img, 
            FeatureExtraction.denom, FeatureExtraction.freq, FeatureExtraction.bw)
        backslash = Preprocessing.backslash_filter(img, 
            FeatureExtraction.denom, FeatureExtraction.freq, FeatureExtraction.bw)
        return np.array(FeatureExtraction.mean_exposure_hist(nbins,frontslash,backslash))

    @staticmethod
    def moments_hu(img):
        """
        returns the last log transformed Hu Moments
        args:
            img: M x N array
        """
        raw = cv2.HuMoments(cv2.moments(img))
        log_trans = -np.sign(raw)*np.log10(np.abs(raw))
        return log_trans.flatten()

    @staticmethod
    def rawpix_nbins(image, nbins):
        """
        extracts raw pixel features and a histogram of nbins
        args:
            image: a m x n standardized shape ndarray representing an image
            nbins: nbins for histogram
        """
        gabor_hist = FeatureExtraction.mean_exposure_hist_from_gabor(image,nbins)
        image = image.flatten()
        return Utils.hStackMatrices(image, gabor_hist)

    @staticmethod
    def moments_nbins(image, nbins):
        moments = FeatureExtraction.moments_hu(image)
        gabor_hist = FeatureExtraction.mean_exposure_hist_from_gabor(image,nbins)
        return np.hstack((moments, gabor_hist))

class ComponentClassifier:

    @staticmethod
    def predict(images, clf, nbins, scaler):
        """ 
        args:
            images: list of PIL images
            clf: classifier object
            nbins: number of bins for the exposure histogram.  This is purely
                   dependent on number of bins the classifier was trained on
        returns:
            list of component labels corresponding to each element in images
        """
        X = None

        for image in images:
            # image comes as a boolean image
            boolean = np.array(image) 
            # We trained it as a nd array w/ values 0 black, 255 white
            integer = np.array(boolean, dtype='int16')
            im = Preprocessing.standardize_shape(integer)
            X = Utils.vStackMatrices(X, FeatureExtraction.moments_nbins(im, nbins))

        X = scaler.transform(X)

        y_pred = clf.predict(X)

        return [Utils.map_label_to_str(label) for label in y_pred]

if __name__ == '__main__':
    pass