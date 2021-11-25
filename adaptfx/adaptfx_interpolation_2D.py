# -*- coding: utf-8 -*-
"""
2D interpolation. In this program the optimal fraction doses are compueted based on a maximal OAR dose while maximizing tumor BED.
single_fraction allows to compute single fraction doses, while whole_plan computes the doses for a whole treatment plan (when all sparing factors are known).
whole_plan_print prints the doses in a well-aranged manner.
"""


import numpy as np
from scipy.stats import truncnorm
import scipy as sc
from scipy.stats import invgamma

def data_fit(data):
    """
    This function fits the alpha and beta value for the conjugate prior

    Parameters
    ----------
    data : array
        a nxk matrix with n the amount of patints and k the amount of sparing factors per patient.

    Returns
    -------
    list
        alpha and beta hyperparameter.
    """
    variances = data.var(axis = 1)
    alpha,loc,beta = invgamma.fit(variances, floc = 0)
    return[alpha,beta]

def get_truncated_normal(mean=0, sd=1, low=0.01, upp=10):
    """
    produces a truncated normal distribution

    Parameters
    ----------
    mean : float, optional
        The default is 0.
    sd : float, optional
        The default is 1.
    low : float, optional
        The default is 0.01.
    upp : float, optional
        The default is 10.

    Returns
    -------
    scipy.stats._distn_infrastructure.rv_frozen
        distribution function.

    """
    return truncnorm((low - mean) / sd, (upp - mean) / sd, loc=mean, scale=sd)

def probdist(X):
    """
    This function produces a probability distribution based on the normal distribution X

    Parameters
    ----------
    X : scipy.stats._distn_infrastructure.rv_frozen
        distribution function.

    Returns
    -------
    prob : list
        list with probabilities for each sparing factor.

    """
    prob = np.zeros(130)
    idx=0
    for i in np.arange(0.01,1.31,0.01):
        prob[idx] = X.cdf(i+0.004999999999999999999)-X.cdf(i-0.005)
        idx +=1
    return prob

def argfind(searched_list,value): 
    """
    This function is used to find the index of certain values.
    searched_list: list/array with values
    value: value that should be inside the list
    return: index of value

    Parameters
    ----------
    searched_list : list/array
        list in which our searched value is.
    value : float
        item inside list.

    Returns
    -------
    index : integer
        index of value inside list.

    """
    index = min(range(len(searched_list)), key=lambda i: abs(searched_list[i]-value))
    return  index

def BED_calc0( dose, ab,sparing = 1):
    """
    calculates the BED for a specific dose

    Parameters
    ----------
    dose : float
        physical dose to be delivered.
    ab : float
        alpha-beta ratio of tissue.
    sparing : float, optional
        sparing factor. The default is 1 (tumor).

    Returns
    -------
    BED : float
        BED to be delivered based on dose, sparing factor and alpha-beta ratio.

    """
    BED = sparing*dose*(1+(sparing*dose)/ab)
    return BED

def BED_calc_matrix( sf, ab,actionspace):
    """
    calculates the BED for an array of values

    Parameters
    ----------
    sf : list/array
        list of sparing factors to calculate the correspondent BED.
    ab : float
        alpha-beta ratio of tissue.
    actionspace : list/array
        doses to be delivered.

    Returns
    -------
    BED : List/array
        list of all future BEDs based on the delivered doses and sparing factors.

    """
    BED = np.outer(sf,actionspace)*(1+np.outer(sf,actionspace)/ab) #produces a sparing factors x actions space array
    return BED

def std_calc(measured_data,alpha,beta):
    """
    calculates the most likely standard deviation for a list of k sparing factors and an inverse-gamma conjugate prior
    measured_data: list/array with k sparing factors

    Parameters
    ----------
    measured_data : list/array
        list/array with k sparing factors
    alpha : float
        shape of inverse-gamma distribution
    beta : float
        scale of inverse-gamme distrinbution

    Returns
    -------
    std : float
        most likely std based on the measured data and inverse-gamma prior

    """  
    n = len(measured_data)
    var_values = np.arange(0.00001,0.25,0.00001)
    likelihood_values = np.zeros(len(var_values))
    for index,value in enumerate(var_values):
        likelihood_values[index] = value**(-alpha-1)/value**(n/2)*np.exp(-beta/value)*np.exp(-np.var(measured_data)*n/(2*value))
    std = (np.sqrt(var_values[np.argmax(likelihood_values)]))
    return std

def distribution_update(sparing_factors,alpha,beta):
    """
    Calculates the probability distributions for all fractions based on a 6 sparing factor list
    Parameters
    ----------
    sparing_factors : array/list
        list/array with 6 sparing factors
    alpha : float
        shape of inverse-gamma distribution
    beta : float
        scale of inverse-gamme distrinbution

    Returns
    -------
    list
        means and stds of all 5 fractions.

    """
    means = np.zeros(len(sparing_factors))
    stds = np.zeros(len(sparing_factors))
    for i in range(len(sparing_factors)):
        means[i] = np.mean(sparing_factors[:(i+1)])
        stds[i] = std_calc(sparing_factors[:(i+1)],alpha,beta)
    means = np.delete(means,0)
    stds = np.delete(stds,0) #we get rid of the first value as it is only the planning value and not used in a fraction
    return [means,stds]


        
def value_eval(fraction,BED,sparing_factors,alpha,beta,abt,abn,bound,fixed_prob = 0, fixed_mean = 0, fixed_std = 0):
    """
    calculates the optimal dose for the desired fraction.

    Parameters
    ----------
    fraction : integer
        number of actual fraction (1 for first, 2 for second, etc.)
    BED : float
        accumulated BED in OAR (from previous fractions) zero in fraction 1

    sparing_factors : list/array
        list of sparing factor distribution.
    alpha : float
        alpha hyperparameter of std prior derived from previous patients.
    beta : float
        beta hyperparameter of std prior derived from previous patients
    abt : float
        alpha-beta ratio of tumor.
    abn : float
        alpha-beta ratio of OAR.
    bound : float
        upper limit of OAR.
    fixed_prob : int
        this variable is to turn on a fixed probability distribution. If the variable is not used (0), then the probability will be updated. If the variable is turned to 1, the inserted mean and std will be used for a fixed sparing factor distribution
    fixed_mean: float
        mean of the fixed sparing factor normal distribution
    fixed_std: float
        standard deviation of the fixed sparing factor normal distribution

    Returns
    -------
    list
        returns a list with Values, policies, OAR dose and tumor dose.

    """
    actual_sparing = sparing_factors[-1]
    if fixed_prob != 1:
        mean = np.mean(sparing_factors) #extract the mean and std to setup the sparingfactor distribution    
        standard_deviation = std_calc(sparing_factors,alpha,beta)
    if fixed_prob == 1:
        mean = fixed_mean
        standard_deviation = fixed_std
    X = get_truncated_normal(mean= mean, sd=standard_deviation, low=0, upp=1.3)
    prob = np.array(probdist(X))
    sf= np.arange(0.01,1.31,0.01)
    sf = sf[prob>0.00001] #get rid of all probabilities below 10^-5
    prob = prob[prob>0.00001]
    
    BEDT = BEDT = np.arange(BED,bound+1.6,1)
    Values = np.zeros(len(BEDT)*len(sf)*(5-fraction)).reshape((5-fraction),len(BEDT),len(sf)) #2d values list with first indice being the BED and second being the sf
    actionspace = np.arange(0,22.4,0.1)
    policy = np.zeros(((5-fraction),len(BEDT),len(sf)))

    
    upperbound = bound+1

    delivered_doses = BED_calc_matrix(sf,abn,actionspace)            
    BEDT_rew = BED_calc_matrix(1, abt,actionspace) #this is the reward for the dose deposited inside the tumor. 
    BEDT_transformed, meaningless = np.meshgrid(BEDT_rew,np.zeros(len(sf)))
    
    for index,frac_state in enumerate(np.arange(fraction,6)): #We have five fractionations with 2 special cases 0 and 4
        if index == 4: #first state with no prior dose delivered so we dont loop through BEDT
            future_bed = BED + delivered_doses
            future_bed[future_bed > bound] = upperbound #any dose surpassing the upper bound will be set to the upper bound which will be penalized strongly
            value_interpolation = sc.interpolate.interp2d(sf,BEDT,Values[index-1])
            future_value = np.zeros(len(sf)*len(actionspace)*len(sf)).reshape(len(sf),len(actionspace),len(sf))
            for actual_sf in range(0,len(sf)):
                future_value[actual_sf] = value_interpolation(sf,future_bed[actual_sf])
            future_values_prob = (future_value*prob).sum(axis = 2) #in this array are all future values multiplied with the probability of getting there. shape = sparing factors x actionspace
            penalties = np.zeros(future_bed.shape)
            penalties[future_bed > bound] = -1000 #penalizing in each fraction is needed. If not, once the algorithm reached the upper bound, it would just deliver maximum dose over and over again
            Vs = future_values_prob + BEDT_transformed + penalties
            
            actual_policy = Vs.argmax(axis=1)
            actual_value = Vs.max(axis=1)
        
        else:
            if index == 5-fraction: #if we are in the actual fraction we do not need to check all possible BED states but only the one we are in
                if fraction != 5:
                    future_bed = BED + delivered_doses
                    future_bed[future_bed > bound] = upperbound #any dose surpassing the upper bound will be set to the upper bound which will be penalized strongly
                    value_interpolation = sc.interpolate.interp2d(sf,BEDT,Values[index-1])
                    future_value = np.zeros(len(sf)*len(actionspace)*len(sf)).reshape(len(sf),len(actionspace),len(sf))
                    for actual_sf in range(0,len(sf)):
                        future_value[actual_sf] = value_interpolation(sf,future_bed[actual_sf])
                    future_values_prob = (future_value*prob).sum(axis = 2) #in this array are all future values multiplied with the probability of getting there. shape = sparing factors x actionspace
                    penalties = np.zeros(future_bed.shape)
                    penalties[future_bed > bound] = -1000 #penalizing in each fraction is needed. If not, once the algorithm reached the upper bound, it would just deliver maximum dose over and over again
                    Vs = future_values_prob + BEDT_transformed + penalties
                    actual_policy = Vs.argmax(axis=1)
                    actual_value = Vs.max(axis=1)  
                else:
                    best_action = (-sf+np.sqrt(sf**2+4*sf**2*(90-BED)/abn))/(2*sf**2/abn)
                    actual_policy = best_action*10
                    actual_value = BED_calc0(best_action,abt)
            else:                    
                for bed_index, bed_value in enumerate(BEDT): #this and the next for loop allow us to loop through all states
                    future_bed = delivered_doses + bed_value
                    future_bed[future_bed > bound] = upperbound #any dose surpassing 90.1 is set to 90.1
                    if index == 0: #last state no more further values to add                    
                        best_action = (-sf+np.sqrt(sf**2+4*sf**2*(90-bed_value)/abn))/(2*sf**2/abn)
                        if bed_value > 90:
                            best_action = np.zeros(best_action.shape)
                        best_action[best_action > 22.3] = 22.3
                        best_action[best_action<0] = 0
                        Values[index][bed_index] = BED_calc0(best_action,abt)                        
                        policy[index][bed_index] = best_action*10 #this one can be pulled before values. in fact we dont want to deliver unlimited amounts of dose
                    else:
                        penalties = np.zeros(future_bed.shape)
                        penalties[future_bed == upperbound] = -1000 
                        value_interpolation = sc.interpolate.interp2d(sf,BEDT,Values[index-1])
                        future_value = np.zeros(len(sf)*224*(len(sf))).reshape(len(sf),224,len(sf))
                        for actual_sf in range(0,len(sf)):
                            future_value[actual_sf] = value_interpolation(sf,future_bed[actual_sf])
                        future_values_prob = (future_value*prob).sum(axis = 2)                        
                        Vs = future_values_prob + BEDT_transformed + penalties
                        best_action = Vs.argmax(axis=1)
                        valer = Vs.max(axis=1)
                        policy[index][bed_index] = best_action
                        Values[index][bed_index] = valer
    index_sf = argfind(sf,actual_sparing)
    dose_delivered_tumor = BED_calc0(actual_policy[index_sf]/10,abt)
    dose_delivered_OAR = BED_calc0(actual_policy[index_sf]/10,abn,actual_sparing)
    total_dose_delivered_OAR = dose_delivered_OAR + BED
    actual_dose_delivered = actual_policy[index_sf]/10

    return [Values,policy,actual_value,actual_policy,dose_delivered_OAR,dose_delivered_tumor,total_dose_delivered_OAR,actual_dose_delivered]
def whole_plan(sparing_factors,OAR_limit,abt,abn,alpha,beta,fixed_prob= 0,fixed_mean = 0,fixed_std =0):
    """
    calculates whole plan given all sparing factors

    Parameters
    ----------
    sparing_factors : list/array
        list/array with all observed sparing factors (6 for a 5 fraction plan).
    OAR_limit : float
        accumulated BED in OAR (from previous fractions) zero in fraction 1
    abt : float
        alpha-beta ratio of tumor.
    abn : float
        alpha-beta ratio of OAR.
    alpha : float
        shape of inverse-gamma distribution
    beta : float
        scale of inverse-gamme distrinbution
    fixed_prob : int
        this variable is to turn on a fixed probability distribution. If the variable is not used (0), then the probability will be updated. If the variable is turned to 1, the inserted mean and std will be used for a fixed sparing factor distribution
    fixed_mean: float
        mean of the fixed sparing factor normal distribution
    fixed_std: float
        standard deviation of the fixed sparing factor normal distribution

    Returns
    -------
    None.

    """
    total_dose_delivered_OAR = 0
    total_tumor_dose = 0
    tumor_doses = np.zeros(5)
    OAR_doses = np.zeros(5)
    physical_doses = np.zeros(5)
    for looper in range(0,5):
        [Values,policy,actual_value,actual_policy,dose_delivered_OAR,tumor_dose,total_dose_delivered_OAR,actual_dose_delivered] = value_eval(looper+1,total_dose_delivered_OAR,sparing_factors[:looper+2],alpha,beta,abt,abn,OAR_limit,fixed_prob, fixed_mean, fixed_std)
        tumor_doses[looper] = tumor_dose
        physical_doses[looper] = actual_dose_delivered
        OAR_doses[looper] = dose_delivered_OAR     
        total_tumor_dose += tumor_dose
    return [tumor_doses,OAR_doses,physical_doses]

def whole_plan_print(sparing_factors,OAR_limit,abt,abn,alpha,beta, fixed_prob = 0, fixed_mean = 0, fixed_std = 0):
    [tumor_doses,OAR_doses,physical_doses] = whole_plan(sparing_factors,OAR_limit,abt,abn,alpha,beta,fixed_prob,fixed_mean,fixed_std)
    for i in range(0,5):
        print('Fraction ',(i+1))
        print('physical dose delivered  = ',physical_doses[i])
        print('tumor dose in BED = ', tumor_doses[i])
        print('OAR dose in BED = ', OAR_doses[i])
    print('total tumor BED = ',np.sum(tumor_doses))
    
def single_fraction(sparing_factors,accumulated_OAR_BED, OAR_limit, abt, abn, alpha, beta,fixed_prob = 0, fixed_mean = 0, fixed_std = 0):
    """

    Parameters
    ----------
    sparing_factors : list/array
        list/array with all observed sparing factors (6 for a 5 fraction plan).
    accumulated_OAR_BED : float
        Total BE delivered to the OAR so far.        
    OAR_limit : float
        accumulated BED in OAR (from previous fractions) zero in fraction 1
    abt : float
        alpha-beta ratio of tumor.
    abn : float
        alpha-beta ratio of OAR.
    alpha : float
        shape of inverse-gamma distribution
    beta : float
        scale of inverse-gamme distrinbution 
    fixed_prob : int
        this variable is to turn on a fixed probability distribution. If the variable is not used (0), then the probability will be updated. If the variable is turned to 1, the inserted mean and std will be used for a fixed sparing factor distribution
    fixed_mean: float
        mean of the fixed sparing factor normal distribution
    fixed_std: float
        standard deviation of the fixed sparing factor normal distribution    
   
    Returns
    -------
    None.

    """
    [Values,policy,actual_value,actual_policy,dose_delivered_OAR,tumor_dose,total_dose_delivered_OAR,actual_dose_delivered] = value_eval(len(sparing_factors)-1,accumulated_OAR_BED,sparing_factors,alpha,beta,abt,abn,OAR_limit,fixed_prob, fixed_mean,fixed_std)
    print('fraction', (len(sparing_factors)-1))
    print('physical dose delivered  = ',actual_dose_delivered)
    print('tumor dose in BED = ', tumor_dose)
    print('OAR dose in BED = ', dose_delivered_OAR)    
