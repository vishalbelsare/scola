import numpy as np
from scipy import linalg
from scipy import sparse
from scipy import stats
import pickle
import os
from functools import partial

class cvFilter():
	
	def __init__(self):
		pass

	def optimize_threshold(self, _filter_, sCov, nCov, sampleNum, null_model_complexity, alphalist = None, disp=False, gamma = 0.5, filename=None, max_density =0.2):	
	
		# Setting candidate threshold values	
		if alphalist is None:
			alphalist = _filter_.candidateThreshold(sCov, nCov, num=30)
		else:
			alphalist = alphalist
	
		
		# Scan each candidate threshold 	
		N = sCov.shape[0] 
		dCov = np.matrix(np.zeros((N, N)))
		dCovList_ = []
		dCov_ = None
		bic_ = 1e+30 
		alpha_ = None
		pvalue_ = None
		isScanned = np.zeros(len(alphalist))

		if filename is not None:
			if os.path.exists(filename): # if touched, then go to the next one
				with open(filename, 'rb') as f: 
					res = pickle.load(f)
					dCov = res["dCovList"][res["lastAid"]]["dCov"]
					dCovList_ = res["dCovList"]
					dCov_ = res["dCov"]
					bic_ = res["bic"] 
					alpha_ = res["alpha"] 
					pvalue_ = res["pvalue"]	
					for r in dCovList_:
						l = r["alpha"] == alphalist
						if np.any(l):
							isScanned[l] = 1 


		if disp:
			print('  \talpha  \tDensity\tp-value\tBIC')

		for aid, alpha in enumerate(alphalist):
			
			if isScanned[aid] == 1:
				continue
	
			#dCov = _filter_.fit(sCov, nCov, dCov, alpha, True)
			#dCov = np.matrix(np.zeros((N, N)))
			dCov = _filter_.fit(sCov, nCov, dCov, sampleNum, alpha)
	
			density = np.sum(np.abs(dCov)>1e-30)/ (N * (N - 1))
			pvalue = self._likelihood_ratio_test(dCov, sCov, nCov, sampleNum)
			bic = self._calc_bic(dCov, sCov, nCov, sampleNum, gamma, null_model_complexity)
		
			mark = ""	
			if (bic_ > bic) | (dCov_ is None):
				dCov_ = dCov
				alpha_ = alpha
				pvalue_ = pvalue 
				bic_ = bic
				mark = " (*)"
			
			if disp:
				density = np.sum(np.abs(dCov)>1e-30) / (N * (N-1))
				print("%2d\t%f\t%f\t%f\t%f%s" % (aid, alpha, density, pvalue, bic, mark))	

			dCovList_ += [{'dCov':dCov, 'alpha':alpha}]
	
			if filename is not None:

				with open(filename, "wb") as f:

					pickle.dump({'lastAlpha:':alpha, 'lastAid':aid, 'dCov':dCov_, 'alpha':alpha_, 'pvalue':pvalue_, 'bic':bic_, 'gamma':gamma, 'dCovList':dCovList_, 'alphaList':alphalist, 'null_model':null_model_complexity}, f)
		
			isScanned[aid] = 1
				
			if density > max_density:
				break

		return {'dCov':dCov_, 'alpha':alpha_, 'pvalue':pvalue_, 'bic':bic_, 'gamma':gamma, 'dCovList':dCovList_, 'alphaList':alphalist, 'null_model':null_model_complexity}
	
	
	
	# Log likelihood
	def _loglikelihood(self, dCov, sCov, nCov, eig_cutoff = 1e-30):
		Cov = dCov + nCov
		w, v = np.linalg.eig(Cov)
		if np.min(w) < 0:
			v = v[:,w>0]
			w = w[w>0]
			iCov = np.real(v @ np.diag(1/w) @ v.T)
			return -0.5 *  np.prod(w) - 0.5*np.trace(sCov @ iCov) - 0.5 * Cov.shape[0] * np.log(2 * np.pi)
		s, v = np.linalg.slogdet(Cov)
		return -0.5 *  s * v  - 0.5*np.trace(sCov @ linalg.inv(Cov)) - 0.5 * Cov.shape[0] * np.log(2 * np.pi)
#		Cov = dCov + nCov
#		w, v = np.linalg.eig(Cov)
#		w = np.real(w)
#		s = np.abs(w) > eig_cutoff
#		w = w[s]
#		v = v[:, s]
#		logdet = np.sum(np.log(w))
#		iCov = v @ np.diag(1/w) @ v.T
#		if np.min(w) < 0:
#			return np.nan 
#		return -0.5 *  logdet  - 0.5*np.trace(sCov @ iCov) - 0.5 * Cov.shape[0] * np.log(2 * np.pi)
	
	# Compute (extended) Baysian Information Criterion
	def _calc_bic(self, dCov, sCov, nCov, sampleNum, gamma, null_model_complexity = 0):
		k = null_model_complexity
		k+= np.sum(np.abs(dCov)>1e-30)/2
		bic = np.log(sampleNum) * k - 2 * sampleNum * self._loglikelihood(dCov, sCov, nCov)
		bic+= 4 * gamma * k * np.log(dCov.shape[0])
		return bic 
		
	# Likelihood ratio test	
	def _likelihood_ratio_test(self, dCov, sCov, nCov, sampleNum):
		try:
			c = -2 * sampleNum * (self._loglikelihood(dCov * 0, sCov, nCov) - self._loglikelihood(dCov, sCov, nCov))
			k= np.sum(np.abs(dCov)>1e-30) / 2
			if k < 1:
				return 1
			pval = 1 - np.exp(stats.chi2.logcdf(c, k))
			return pval
		except:
			return 1

