# -*- coding: utf-8 -*-
# Author: J.J. Snell & S.G. van Leipsig
# supervised by dr. M. Meeter
# 01-07-15
# Reading simulation involving Open Bigram processing

from __future__ import division
from collections import defaultdict
import math
import re
from reading_common import stringToBigramsAndLocations, calcBigramExtInput, calcMonogramExtInput, get_stimulus_text_from_file, calc_word_attention_right
from reading_functions import my_print, get_threshold, getMidwordPositionForSurroundingWord, is_similar_word_length, \
    calc_saccade_error, norm_distribution, normalize_pred_values
from read_saccade_data import get_freq_pred_files
from speed_testing import bigram_activation, bigram_activation_set, bigram_activation_set_fast, monogram_activation_list,\
    monogram_activation_set, bigram_activation_set_fast2, word_activations, word_activations2
import pdb
import numpy as np
from numpy import testing
import pickle
import parameters as pm
import sys
import io
import os
if pm.visualise:
    import Visualise_reading


##TODO calling dictionary with string is slightly faster than with integer!, for clarity use string/word in dictionaries

def reading_simulation(filename, parameters):

    if any(parameters):
#        pm.decay = parameters[0]
#        pm.bigram_to_word_excitation = parameters[1]
#        pm.bigram_to_word_inhibition = parameters[2]
#        pm.word_inhibition = parameters[3]
#        pm.max_activity = parameters[4]
#        pm.max_attend_width = int(parameters[5])
#        pm.min_attend_width = int(parameters[6])
#        pm.attention_skew = parameters[7]
#        pm.bigram_gap = int(parameters[8])
#        pm.min_overlap = int(parameters[9])
#        pm.refix_size = parameters[10]
#        pm.salience_position = parameters[11]
#        pm.sacc_optimal_distance = parameters[12]
#        pm.saccErr_scaler = parameters[13]
        pm.saccErr_sigma = abs(parameters[0])
        pm.saccErr_sigma_scaler = parameters[1]
        pm.mu = parameters[2]
        pm.sigma = parameters[3]
#        pm.distribution_param = parameters[18]
#        pm.wordfreq_p = parameters[19]
#        pm.wordpred_p = parameters[20]


    lexicon = []
    all_data = []
    individual_words = []

    # function input, filename, should be a string of the exact textfile name and path.
    if ".txt" in filename:
        textfile = get_stimulus_text_from_file(filename)
        textsplitbyspace = textfile.split(" ")
    if ".pkl" in filename:
        textsplitbyspace = pickle.load(open(filename))
#        textsplitbyspace = textsplitbyspace[:1000]
    for word in textsplitbyspace:
        if word.strip()!="":
            new_word = unicode(word.strip())  # make sure words are unicode (numpy.unicode_ can cause errors)
            individual_words.append(new_word)
    target_words = []
    target_word_sf = []
    target_word_gd = []
    target_word_refixs = []
    target_word_act = []

#    with open(r'C:\Users\Josh\Desktop\josh work\Experiments\BOB\sam reading model july15\sam reading model july15\PSC\target_positions.txt') as file:
#        target_positions = file.readlines()
#    for i in range(0,len(target_positions)):
#        target_positions[i] = int(target_positions[i].replace('\n',''))
#    print target_positions

<<<<<<< HEAD

    # load dicts for threshold
    if pm.language == "german":
        word_freq_dict, word_pred_values = get_freq_pred_files()
        # Replace prediction values with syntactic probabilities
        if pm.use_grammar_prob:
            sys.path.append("Data")
            with open("Data/PSCALLsyntax_probabilites.pkl","r") as f:
                word_pred_values = pickle.load(f)

    if pm.language == "dutch":
        word_freq_dict = pickle.load(open("Data/nederlands/freq.pkl"))
        word_pred_values = np.ones(len(textsplitbyspace))
        word_pred_values[:] = 0.1
#    pickle.dump([word_freq_dict,word_pred_values],open("Data/freq_pred.pkl", "w"))
    max_frequency_key = max(word_freq_dict, key=word_freq_dict.get)
    max_frequency = word_freq_dict[max_frequency_key]
    print("Length text: "+str(len(individual_words))+"\nLength pred: "+str(len(word_pred_values)))
    word_pred_values = word_pred_values[0:len(individual_words)]
    max_predictability = np.max(word_pred_values)
    min_predictability = np.min(word_pred_values)

    word_thresh_dict = {}
    #Threshold dict for individual words
    for word in individual_words:
        word_thresh_dict[word] = get_threshold(word,word_freq_dict,max_frequency,word_pred_values,pm.wordfreq_p,pm.wordpred_p,pm.wordlen_lin,pm.start_lin)
        try:
            word_freq_dict[word]
        except KeyError:
            word_freq_dict[word] = 0

    #---------------------------------------------------------------------------
    ## Make individual words dependent variables

    TOTAL_WORDS = len(individual_words)
    print "LENGTH of freq dict: "+str(len(word_freq_dict))
    print "LENGTH of individual words: "+str(len(individual_words))
    

    # array with recognition flag for each word position in the text. 
    # is set to true when a word whose length is similar to that of the fixated word, is recognised
    # so if it fulfills the condition is_similar_word_length(fixated_word,other_word)
    recognized_position_flag = np.zeros(len(individual_words),dtype=bool)

    # array with recognition flag for each word in the text
    # it is set to true whenever the exact word from the stimuli is recognized
    recognized_word_at_position_flag = np.zeros(len(individual_words),dtype=bool)
    recognized_word_at_cycle = np.empty(len(individual_words),dtype=int)
    recognized_word_at_cycle.fill(-1)

    # array in which I store the history of regressions
    # is set to true at a certain position in the text when a regression is performed to that word
    regression_flag = np.zeros(len(individual_words),dtype=bool)

    #---------------------------------------------------------------------------
    ## Make lexicon. Makes sure lexicon contains no double words.

    for i in xrange(len(individual_words)):
        if individual_words[i] not in lexicon:
            lexicon.append(individual_words[i])
    print "size lexicon before freq: "+str(len(lexicon))
    if(len(word_freq_dict)>0):
        for freq_word in word_freq_dict.keys():
            if freq_word not in lexicon:
                lexicon.append(freq_word.lower())

    print "size lexicon after freq: "+str(len(lexicon))
    lexicon_file_name = 'Data/Lexicon.dat'
    with open(lexicon_file_name,"w") as f:
        pickle.dump(lexicon, f)
    f.close()
    #sort alphabetically ... for debugging purposes (doesn't affect simulation)
    lexicon.sort()

    #---------------------------------------------------------------------------
    ## Make lexicon dependent variables
    LEXICON_SIZE = len(lexicon)

    # Normalize word inhibition to the size of the lexicon. 
    lexicon_normalized_word_inhibition = (100.0/LEXICON_SIZE) * pm.word_inhibition

    # Set activation of all words in lexicon to zero and make bigrams for each word.
    lexicon_word_activity = {}
    lexicon_word_bigrams = {}
    lexicon_word_bigrams_set = {}
    lexicon_index_dict = {}

    ## Lexicon word measures
    lexicon_word_activity_np = np.zeros((LEXICON_SIZE),dtype=float)
    lexicon_word_inhibition_np = np.zeros((LEXICON_SIZE),dtype=float)
    lexicon_word_inhibition_np2 = np.zeros((LEXICON_SIZE),dtype=float)
    lexicon_activewords_np = np.zeros((LEXICON_SIZE),dtype=int)
    word_input_np = np.zeros((LEXICON_SIZE),dtype=float)
    lexicon_thresholds_np = np.zeros((LEXICON_SIZE),dtype=float)

    for i,word in enumerate(lexicon):
        lexicon_thresholds_np[i] = get_threshold(word,word_freq_dict,max_frequency,word_pred_values,pm.wordfreq_p,pm.wordpred_p,pm.wordlen_lin,pm.start_lin)+0.014*len(lexicon[i])**1.15 
        lexicon_index_dict[word] = i
        lexicon_word_activity[word] = 0.0

    # lexicon indices for each word of text (individual_words)
    individual_to_lexicon_indices = np.zeros((len(individual_words)),dtype=int)
    for i,word in enumerate(individual_words):
        individual_to_lexicon_indices[i] = lexicon.index(word)

    ## lexicon bigram dict
    for word in xrange(LEXICON_SIZE):
        lexicon[word] = " "+lexicon[word]+" "
        [all_word_ngrams, bigramLocations] = stringToBigramsAndLocations(" "+lexicon[word]+" ")
        all_word_bigrams = []
        #all_word_bigrams = set()

        for ngram in all_word_ngrams:
            if len(ngram)==2:
                all_word_bigrams.append(ngram)
        lexicon[word] = lexicon[word][1:(len(lexicon[word])-1)]
        lexicon_word_bigrams[lexicon[word]] = all_word_bigrams

    print "Amount of words in lexicon: ",LEXICON_SIZE
    print "Amount of words in text:",TOTAL_WORDS
    print ""

#-----------------------------------------------------------------------------------------
    print "Setting up word-to-word inhibition grid..."

    # Set up the list of word inhibition pairs, with amount of bigram/monograms overlaps for every pair.
    #initialize inhibition matrix with false
    #word_inhibition_matrix = np.zeros((LEXICON_SIZE,LEXICON_SIZE),dtype=bool)
    word_overlap_matrix = np.zeros((LEXICON_SIZE,LEXICON_SIZE),dtype=int)

    complete_selective_word_inhibition = True
    overlap_list = {}
    for other_word in xrange(LEXICON_SIZE):
        for word in xrange(LEXICON_SIZE):
            if lexicon[word]==lexicon[other_word]:
                continue

            #elif word_inhibition_matrix[other_word,word]==False: and is_similar_word_length(lexicon[word],lexicon[other_word]):
            else:
                bigrams_common = []
                bigrams_append = bigrams_common.append
                bigram_overlap_counter = 0
                for bigram in xrange(len(lexicon_word_bigrams[lexicon[word]])):
                    if lexicon_word_bigrams[lexicon[word]][bigram] in lexicon_word_bigrams[lexicon[other_word]]:
                        bigrams_append(lexicon_word_bigrams[lexicon[word]][bigram])
                        lexicon_word_bigrams_set[lexicon[word]] = set(lexicon_word_bigrams[lexicon[word]])
                        bigram_overlap_counter += 1

                monograms_common = []
                monograms_append = monograms_common.append
                monogram_overlap_counter = 0

                unique_word_letters = ''.join(set(lexicon[word]))
                for pos in xrange(len(unique_word_letters)):
                    monogram = unique_word_letters[pos]
                    if monogram in lexicon[other_word]:
                        monograms_append(monogram)
                        monogram_overlap_counter +=1

                #take into account both bigrams and monograms for inhibition counters (equally)
                total_overlap_counter = bigram_overlap_counter + monogram_overlap_counter

                min_overlap = pm.min_overlap
                if complete_selective_word_inhibition:
                    if total_overlap_counter > min_overlap:
                        word_overlap_matrix[word,other_word] = total_overlap_counter - min_overlap
                    else:
                        word_overlap_matrix[word,other_word] = 0
                else: ## is_similar_word_length
                    if total_overlap_counter > min_overlap:
                        word_inhibition_matrix[word,other_word]=True
                        word_inhibition_matrix[other_word,word]=True
                        overlap_list[word,other_word] = total_overlap_counter - min_overlap
                        overlap_list[other_word,word] = total_overlap_counter - min_overlap
                        sys.exit('Make sure to use slow version, fast/vectorized version not compatible')



    # Save overlap matrix, with individual words selected
    #C:/Users/SAM/PycharmProjects/StageVu/
    output_inhibition_matrix = 'Data/Inhibition_matrix.dat'
    with open(output_inhibition_matrix,"w") as f:
        #pickle.dump(word_overlap_matrix[individual_to_lexicon_indices],f)
        pickle.dump(np.sum(word_overlap_matrix,axis=0)[individual_to_lexicon_indices],f)
        # print np.sum(word_overlap_matrix,axis=0)[individual_to_lexicon_indices]


    print "Inhibition grid ready."
    print ""
  #---------------------------------------------------------------------------
    print "BEGIN READING"
    print ""
    print ""
    print ""
    print ""

    ## Initialize
    ## Parameters

    total_reading_time = 0
    regression = False
    wordskip = False
    refixation = False
    forward = False
    saccade_distance = 0 # amount of characters
    fixation_duration = 0
    end_of_text = False  # Is set to true when end of text is reached.
    fixation = 0  # The iterator that indicates the element of fixation in the text
    # (this iterator can go backwards as well, with regressions).

    fixation_counter = 0 # The iterator that increases +1 with every next fixation,
    # to expand all_data with every next fixation.

    # If eye position is to be in a position other than that of the word middle, offset will be negative/positive (left/right)
    # and will represent the number of letters to the new position. It's value is reset before a new saccade is performed.
    OffsetFromWordCenter = 0
    Offset_previous = 0
    attendWidth = 4.0
    nextEyePosition = 0
    saccade_distance= 0
    saccade_error = 0

    refixation_type = 0
    wordskip_pass = 0
    saccade_type_by_error = 0

    attendposition_change = False
    attendposition_change_counter = 0
    width_change_delay = 0

    CYCLE_SIZE = 25
    allocated_dict = defaultdict(list)
    salience_position_new = pm.salience_position

    previous_fixated_words = None
    previous_lexicon_values = None
    reset_pred_previous = False

    N_in_allocated = 0
    N1_in_allocated = 0
    to_pauze = False

    if pm.visualise:
        Visualise_reading

    #---------------------------------------------------------------------------

    ## BEGIN TO READ :
    while end_of_text == False:

        my_print("***********************************")
        my_print("offset", OffsetFromWordCenter, "attendWidth:", attendWidth)

        print('fixation_pos-'+str(fixation))

        #make sure that fixation does not go over the end of the text
        fixation = min(fixation,TOTAL_WORDS-1)

        #TODO, because only 1 word is added, can be replaced with numpy individual words array
        already_allocated =[]
        if fixation-2 >= 0:
            if regression:
                already_allocated = allocated_dict[fixation-1] + allocated_dict[fixation+1]
            elif wordskip: # + works because of defaultdict is list!
                already_allocated =  allocated_dict[fixation-3] + allocated_dict[fixation-2] + allocated_dict[fixation-1]
                ##Delete words outside stimulus
                for key in [k for k in allocated_dict.keys() if k < fixation-3] : del allocated_dict[key]
            else:
                already_allocated =  allocated_dict[fixation-2] + allocated_dict[fixation-1]
                for key in [k for k in allocated_dict.keys() if k < fixation-2] : del allocated_dict[key]

        # ##Test the allocation
        my_print( "ALLOCATED:",already_allocated,allocated_dict.keys())
        for i in already_allocated:
            try:
                print lexicon[i]
            except:
                print "Escaping annoying encoding error while printing"
            if not regression and i == individual_to_lexicon_indices[fixation]:
                N_in_allocated += 1
                to_pauze = True
            if not regression and (fixation+1 <= len(individual_words)-1) and (i == individual_to_lexicon_indices[fixation+1]):
                N1_in_allocated += 1
                to_pauze = True
        print

        # To find the words that are wrongly allocated
        if pm.pauze_allocation_errors and to_pauze:
            print "PAUSE, type anything to continue"
            response  = raw_input()
            to_pauze=False
            print norm_pred_values

        saccade_time = CYCLE_SIZE * (saccade_distance/8.0) # elapsed time during eye movement, in milliseconds  #todo why 8.0??
        total_reading_time += saccade_time+fixation_duration  # This variable is not really used as of yet; perhaps in later experiments. # TODO maybe also put in all_data

        if pm.slow_word_activity:
            for word in xrange(len(lexicon_word_activity)):
                if lexicon_word_activity[lexicon[word]] < pm.min_activity:
                    lexicon_word_activity[lexicon[word]] = pm.min_activity

        lexicon_word_activity_np[lexicon_word_activity_np < pm.min_activity] = pm.min_activity


        ## Actual wordskips are not included in all_data!
        all_data.append({})
        all_data[fixation_counter] = {'foveal word': individual_words[fixation], 'foveal word text index':fixation, 'stimulus':[],
                                      'word activities per cycle':[],'fixation duration':0, 'recognized words indices':[],
                                      'attentional width':attendWidth,'exact recognized words positions':[],'eye position':0,
                                      'refixated':refixation, 'wordskipped':wordskip, 'regressed':regression,
                                      'forward':forward, 'fixation word activities':[],'word threshold':0, 'word frequency':0,
                                      'word predictability':0, 'saccade error':saccade_error,
                                      'saccade distance':int(round(saccade_distance)),'wordskip pass':wordskip_pass,
                                      'refixation type':refixation_type,'saccade_type_by_error':saccade_type_by_error,
                                      'Offset':OffsetFromWordCenter,'relative landing position':Offset_previous}


        Offset_previous = round(OffsetFromWordCenter)

        # Re-define the stimulus and calculate eye position, saccade error is implemented in OffsetFromWordCenter
        if fixation-2 == -2:
            stimulus = " "+individual_words[fixation]+" "+individual_words[fixation+1]+" "+individual_words[fixation+2]+" "
            EyePosition =  round(len(individual_words[fixation])*0.5) + OffsetFromWordCenter
        elif fixation-2 == -1:
            stimulus = " "+individual_words[fixation-1]+" "+individual_words[fixation]+" "+individual_words[fixation+1]+" "+individual_words[fixation+2]+" "
            EyePosition =  round(len(individual_words[fixation])*0.5) + len(individual_words[fixation-1]) + 1 + OffsetFromWordCenter
        elif fixation+2 == TOTAL_WORDS+1:
            stimulus = " "+individual_words[fixation-2]+" "+individual_words[fixation-1]+" "+individual_words[fixation]+" "
            EyePosition = len(individual_words[fixation-2]) + len(individual_words[fixation-1]) +  round(len(individual_words[fixation])*0.5) + 2 + OffsetFromWordCenter
        elif fixation+2 == TOTAL_WORDS:
            stimulus = " "+individual_words[fixation-2]+" "+individual_words[fixation-1]+" "+individual_words[fixation]+" "+individual_words[fixation+1]+" "
            EyePosition = len(individual_words[fixation-2]) + len(individual_words[fixation-1]) +  round(len(individual_words[fixation])*0.5) + 2 + OffsetFromWordCenter
        elif fixation-2 == 0:
            stimulus = " "+individual_words[fixation-2]+" "+individual_words[fixation-1]+" "+individual_words[fixation]+" "+individual_words[fixation+1]+" "+individual_words[fixation+2]+" "
            EyePosition =  round(len(individual_words[fixation])*0.5) + len(individual_words[fixation-1]) + len(individual_words[fixation-2]) + 2 + OffsetFromWordCenter
        else:
            stimulus = " "+individual_words[fixation-2]+" "+individual_words[fixation-1]+" "+individual_words[fixation]+" "+individual_words[fixation+1]+" "+individual_words[fixation+2]+" "
            EyePosition = round(len(individual_words[fixation])*0.5) + len(individual_words[fixation-1]) + len(individual_words[fixation-2]) + 2 + OffsetFromWordCenter

        #make sure that eyeposition is an integer
        EyePosition = int(round(EyePosition))
        my_print( "Start Eye:",OffsetFromWordCenter,stimulus[EyePosition:EyePosition+4])

        #as part of the saccade, narrow attention width by 2 letters in the case of regressions or widen it by 0.5 letters in forward saccades
        if regression:
            attendWidth=max(attendWidth-2.0,pm.min_attend_width)
        elif not refixation:
            attendWidth=min(attendWidth+0.5,pm.max_attend_width)

        if pm.visualise:
            Visualise_reading.update_stimulus(stimulus,EyePosition,attendWidth,EyePosition,fixation)
            Visualise_reading.main()
            Visualise_reading.save_screen(fixation_counter,"")

        # set regression flag to know that a regression has been realized towards this position,
        # in order to prevent double regressions to the same word
        if regression:
            regression_flag[fixation] = True

        # 1 refixation not recognized, 2 refixation by activity
        refixation_type = 0
        wordskip_pass = 0

        my_print('attendWidth',attendWidth)

       # These parameters may be set to True if a wordskip or regression needs to be done.
       # This will influence where the eyes move, (see bottom of the code).
        if wordskip == True:
            wordskip = False
        if refixation == True:
            refixation = False
        if regression == True:
            regression = False
        if forward == True:
            forward = False

        crt_fixation_word_activities_np = np.zeros((25,7),dtype=float)

        # Fill in entries into all_data
        all_data[fixation_counter]['stimulus']=stimulus
        all_data[fixation_counter]['eye position']=EyePosition
        for word in xrange(len(stimulus.split(" "))-2):
            all_data[fixation_counter]['word activities per cycle'].append({stimulus.split(" ")[word+1]:[]})
            # Above: "Word activities per cycle" is a dict containing the stimulus' words. For every word there is a list that will keep track of the activity per cycle.
        
    #------------------------------------------------------------------------------
        # Only stimulus bigrams, monograms are in allNgrams
        # bigramsToLocations = (firstloc, secondloc, weight)
        [allNgrams, bigramsToLocations] = stringToBigramsAndLocations(stimulus)
        allMonograms = []
        allBigrams = []

        for ngram in allNgrams:
            if(len(ngram)==2):
                allBigrams.append(ngram)
            else:
                allMonograms.append(ngram)
        allBigrams_set = set(allBigrams)
        allMonograms_set = set(allMonograms)


    #-------------------------------------------------------------------------------

        # At this point, stimulus, bigrams and weights for the current stimulus are defined. Now prepare for entering
        # the cycle-loop that builds word activity with every cycle.
        my_print("fixation: ",individual_words[fixation])
	try:
	        with open("bot.txt","w") as f:
			f.write("Word number "+str(fixation)+": "+unicode(str(individual_words[fixation])))
	except:
		print("woops")
	my_print("stimulus: ",stimulus)
        #print 'EyePostition:',EyePosition

        amount_of_cycles = 0
        amount_of_cycles_since_attention_shifted = 0

        shift = False
        AttentionPosition = EyePosition

        #this is the position of the first letter that is at the right of the middle of the fixation word
        fixationFirstPositionRightToMiddle = None
        fixationFirstPositionLeftToMiddle = None

        #substract offset to get the fixation word actual center position (used to calculate first/last index)
        fixationCenter = EyePosition - int(round(OffsetFromWordCenter))

        centerWordFirstLetterIndex = None
        centerWordLastLetterIndex = None

        #identify the beginning and end of fixation word by looking at the first letter following a space, counted to the left of the center,
        #and the first letter followed by a space, counted to the right from the center
        for letter_index in xrange(int(fixationCenter),len(stimulus)):
            if stimulus[letter_index]==" ":
                centerWordLastLetterIndex = letter_index-1
                if (centerWordLastLetterIndex == len(stimulus)-1):
                    assert(fixation==TOTAL_WORDS-1) #can only happen for last word
                break

        for letter_index_reversed in xrange(int(fixationCenter),-1,-1):
            if stimulus[letter_index_reversed]==" ":
                centerWordFirstLetterIndex = letter_index_reversed+1
                break

        # Check if first/lastPosititionToMiddle doesn't excede word
        if len(individual_words[fixation]) % 2 == 1 and EyePosition != centerWordFirstLetterIndex:
            fixationFirstPositionLeftToMiddle=EyePosition-1
            fixationFirstPositionRightToMiddle=EyePosition+1
        else:
            fixationFirstPositionLeftToMiddle=EyePosition
            fixationFirstPositionRightToMiddle=EyePosition+1

        stimulus_before_eyepos = stimulus[0:fixationFirstPositionLeftToMiddle+1]
        stimulus_after_eyepos = stimulus[fixationFirstPositionRightToMiddle:-1]

        # CHECK UNICODE
        if type(stimulus) is unicode:
            p = re.compile(r'\b\w+\b',re.UNICODE)
        else:
            p = re.compile(r'\b\w+\b')

        leftWordEdgeLetterIndexes = []
        rightWordEdgeLetterIndexes = []

        #Get word edges for all words starting with the word at fixation (taking into account only the right side of the word)
        for m in p.finditer(stimulus_before_eyepos):
            #add position of the first letter
            leftWordEdgeLetterIndexes.append((m.start(),m.end()-1))

        #todo gives errors when on last letter of words-1 word
        for m in p.finditer(stimulus_after_eyepos):
            #add position of the first letter, [0][0] = current fixation position + 1
            rightWordEdgeLetterIndexes.append((fixationFirstPositionRightToMiddle+m.start(),fixationFirstPositionRightToMiddle+ m.end()-1))

        assert(rightWordEdgeLetterIndexes != []) # when error -> eyeposition at final letter of text

        #TODO think about method of leftword/rightword indices -> maybe better to used fixed edge-indices with eyeposition
        #append some empty edges to make sure activity for current word is 0, if I am at its right or left edge
        if leftWordEdgeLetterIndexes[-1][1]<centerWordFirstLetterIndex:
            leftWordEdgeLetterIndexes.append(( -1,-1 ))
        if rightWordEdgeLetterIndexes[0][0]>centerWordLastLetterIndex:
            rightWordEdgeLetterIndexes.insert(0,( -1,-1 ))

        #Test rightWordEdgeLetterIndexes
        if fixation < TOTAL_WORDS-3:
            assert(len(rightWordEdgeLetterIndexes) == 3)

        if reset_pred_previous:
            lexicon_thresholds_np[previous_fixated_words] = previous_lexicon_values
            reset_pred_previous = False

        ## Adjust lexicon thresholds with predictability values, only when words in stimulus
        fix_start = (fixation-1) if (fixation > 0) else fixation
        fix_end = (fixation+2) if (fixation < TOTAL_WORDS) else fixation
        lexicon_fixated_words = individual_to_lexicon_indices[fix_start:fix_end]
        norm_pred_values = normalize_pred_values(pm.wordpred_p,word_pred_values[fix_start:fix_end])
        previous_fixated_words = lexicon_fixated_words
        previous_lexicon_values = lexicon_thresholds_np[lexicon_fixated_words]
        reset_pred_previous = True
        lexicon_thresholds_np[lexicon_fixated_words] = lexicon_thresholds_np[lexicon_fixated_words] * norm_pred_values

        # print OffsetFromWordCenter
        # print stimulus
        # print stimulus_before_eyepos
        # print stimulus_after_eyepos
        # print leftWordEdgeLetterIndexes
        # print rightWordEdgeLetterIndexes

    #-------------------------------------------------------------------------------------------

        while (amount_of_cycles_since_attention_shifted < 5): # A saccade program takes 5 cycles, or 125ms.
                                                        # this counter starts counting at saccade program initiation.


            unitActivations = {} # reset after each fixation
            lexicon_activewords = [] # Only the words in this list will later participate in word-to-word inhibition.
                                             # As such, less word overlap pairs will be called when calculating inhibition,
                                             # so to speed up the code.
                                             # Stores the indexes of the words in the lexicon are stored.
            ## Reset
            word_input = []
            word_input_np.fill(0.0)
            lexicon_word_inhibition_np.fill(0.0)
            lexicon_word_inhibition_np2.fill(0.0)
            lexicon_activewords_np.fill(False)
            # assert(lexicon_activewords_np.all()==False)
            # assert(word_input_np.all()==0.0)
            # assert(lexicon_word_inhibition_np.all()==0.0)

            crt_fixation_word_activities = [0,0,0,0,0]

            # Calculate bigram and monogram activity:
            for ngram in allNgrams:
                if len(ngram)==2:
                    unitActivations[ngram] = calcBigramExtInput(ngram, bigramsToLocations, EyePosition, AttentionPosition, attendWidth, shift, amount_of_cycles)
                else:
                    unitActivations[ngram] = calcMonogramExtInput(ngram, bigramsToLocations, EyePosition, AttentionPosition, attendWidth, shift, amount_of_cycles)


            # Increase salience attentionposition for N+1 predictable words,
            # only used for calculation word_attention_right (salience), change is reset after actual attention shift
            if recognized_position_flag[fixation] == True and shift == False and fixation < TOTAL_WORDS-1 and pm.use_attendposition_change == True:
                if attendposition_change == False:
                    try:
                        pred = word_pred_values[fixation+1]
                        salience_position_new += (pm.salience_position * pred)
                        attendposition_change = True
                        attendposition_change_counter = 0
                    except KeyError:
                        pass # predictability too low
                else:
                    attendposition_change_counter +=1

        #----------------------------------------------------------------------------


            # Now, calculate word activity as a result of stimulus' ngram activities.
            # Because multiplied with unitActivations, only active (in stimulus) are used

            ## All stimulus bigrams used, therefore the same inhibition for each word of lexicon
            wordBigramsInhibitionInput = 0
            for bigram in allBigrams:
                wordBigramsInhibitionInput += pm.bigram_to_word_inhibition * unitActivations[bigram]
            for monogram in allMonograms:
                wordBigramsInhibitionInput += pm.bigram_to_word_inhibition * unitActivations[monogram]

            for lexicon_ix,lexicon_word in enumerate(lexicon):
                wordExcitationInput = 0
                for ln in range(1,len(stimulus.split(' '))-2):
                    if is_similar_word_length(lexicon[lexicon_ix],stimulus.split(' ')[ln]):

                        # ##Speed testing bigram functions, Fastest-> bigram_activation_set_fast
                        # wordExcitationInput = bigram_activation(lexicon_word,allBigrams,lexicon_word_bigrams,unitActivations)
                        # wordExcitationInput = bigram_activation_set(lexicon_word,allBigrams_set,lexicon_word_bigrams_set,unitActivations)
                        # wordExcitationInput1 = bigram_activation_set_fast(lexicon_word,allBigrams_set,lexicon_word_bigrams_set,unitActivations)
                        # wordExcitationInput2 = bigram_activation_set_fast2(lexicon_word,allBigrams_set,lexicon_word_bigrams_set,unitActivations)

                        # ##Speed testing monogram functions, Fastest -> monogram_activation_list
                        # wordExcitationInput1m = monogram_activation_list(lexicon_word,allMonograms,lexicon_word_bigrams,unitActivations)
                        # wordExcitationInput2m = monogram_activation_list2(lexicon_word,allMonograms_set,lexicon_word_bigrams,unitActivations)
                        # wordExcitationInput3m = monogram_activation_set(lexicon_word,allMonograms_set,lexicon_word_bigrams,unitActivations)
                        ## could use numpy, lexicon as numpy.char and np.intersect1d

                        ## (Fast) Bigram & Monogram activations
                        bigram_intersect_list = allBigrams_set.intersection(lexicon_word_bigrams[lexicon_word])
                        for bigram in bigram_intersect_list:
                            wordExcitationInput+= pm.bigram_to_word_excitation * unitActivations[bigram]
                        for monogram in allMonograms:
                            if monogram in lexicon_word:
                                wordExcitationInput+= pm.bigram_to_word_excitation * unitActivations[monogram]

                        # # ## Slow bigram & monogram activations
                        # wordExcitationInput2 = 0
                        # #wordBigramsInhibitionInput = 0
                        # #bigram excitation or inhibition
                        # for bigram in allBigrams:
                        #     # priming
                        #     if bigram in lexicon_word_bigrams_set[lexicon_word]:
                        #         wordExcitationInput2+= pm.bigram_to_word_excitation * unitActivations[bigram]
                        #     #wordBigramsInhibitionInput += pm.bigram_to_word_inhibition * unitActivations[bigram]
                        #
                        # #monogram excitation & inhibition
                        # for monogram in allMonograms:
                        #     if monogram in lexicon_word:
                        #         wordExcitationInput2+= pm.bigram_to_word_excitation * unitActivations[monogram]
                        #     #wordBigramsInhibitionInput += pm.bigram_to_word_inhibition * unitActivations[monogram]

                        word_input_np[lexicon_ix] = wordExcitationInput + wordBigramsInhibitionInput

                        if lexicon_word == individual_words[fixation] :
                            crt_fixation_word_activities_np[amount_of_cycles,0] = wordExcitationInput
                            crt_fixation_word_activities_np[amount_of_cycles,1] = abs(wordBigramsInhibitionInput)
                            crt_fixation_word_activities[0] = wordExcitationInput
                            crt_fixation_word_activities[1] = abs(wordBigramsInhibitionInput)
                        break

        #----------------------------------------------------------------------------

            # Below: subtract the word-to-word inhibition.
            # This is done by first adding the inhibition activity of every single word to the inhibition
            # counter of the words they have overlap with.
            # Then, all these inhibition counter values can be subtracted from their respective words
            # without having the order in which words are inhibited influence the outcome. (F.e., if you
            # first calculate inhibition for word1, and then word2, word1 has less inhibition on word2
            # than vice versa.)

            ## Active words selection vector
            lexicon_activewords_np[(lexicon_word_activity_np>0.0) | (word_input_np>0.0)] = True
                                                        
            ## Calculate total inhibition for each word

            # ## SPEED TESTING
            # lexicon_word_inhibition_np = word_activations(LEXICON_SIZE,lexicon_activewords_np,word_overlap_matrix,lexicon_normalized_word_inhibition,lexicon_word_activity_np,lexicon_word_inhibition_np)
            # lexicon_word_inhibition_np2 = word_activations2(LEXICON_SIZE,lexicon_activewords_np,word_overlap_matrix,lexicon_normalized_word_inhibition,lexicon_word_activity_np,lexicon_word_inhibition_np)
            # np.testing.assert_allclose(lexicon_word_inhibition_np,lexicon_word_inhibition_np2)
                                                        
            # ## Vector * Vector
            # for word_ix in xrange(LEXICON_SIZE):
            #     inhibiting_words_np = np.where((lexicon_activewords_np == True) & (word_overlap_matrix[word_ix,:]>0))[0]
            #     norm_lexicon_word_activity = lexicon_normalized_word_inhibition * lexicon_word_activity_np[inhibiting_words_np]
            #     total_word_inhibition = np.dot(word_overlap_matrix[word_ix,inhibiting_words_np],norm_lexicon_word_activity)
            #     lexicon_word_inhibition_np[word_ix] = total_word_inhibition

            ## Matrix * Vector (4x faster than vector)
            overlap_select = word_overlap_matrix[:,(lexicon_activewords_np == True)]
            lexicon_select = lexicon_word_activity_np[(lexicon_activewords_np == True)] * lexicon_normalized_word_inhibition
            lexicon_word_inhibition_np = np.dot(overlap_select,lexicon_select)

            ## combine word inhibition and input, and update word activity
            lexicon_total_input_np = np.add(lexicon_word_inhibition_np,word_input_np)
            lexicon_word_activity_new = ((pm.max_activity - lexicon_word_activity_np) * lexicon_total_input_np) + ((lexicon_word_activity_np - pm.min_activity) * pm.decay)
            lexicon_word_activity_np = np.add(lexicon_word_activity_np,lexicon_word_activity_new)

            # Correct words beyond borders of minimum and maximum activity to
            # minimum and maximum activity, respectively.
            lexicon_word_activity_np[lexicon_word_activity_np < pm.min_activity] = pm.min_activity
            lexicon_word_activity_np[lexicon_word_activity_np > pm.max_activity] = pm.max_activity

            ## Save current word activities (per cycle)
            fixation_lexicon_index = individual_to_lexicon_indices[fixation]
            crt_word_total_input_np = lexicon_total_input_np[fixation_lexicon_index]
            crt_word_activity_np = lexicon_word_activity_np[fixation_lexicon_index]
            crt_fixation_word_activities[2]=abs(lexicon_word_inhibition_np[fixation_lexicon_index])
            crt_fixation_word_activities_np[amount_of_cycles,2] = abs(lexicon_word_inhibition_np[fixation_lexicon_index])
            crt_fixation_word_activities_np[amount_of_cycles,5] = (pm.max_activity - crt_word_activity_np) * crt_word_total_input_np
            crt_fixation_word_activities_np[amount_of_cycles,6] = (crt_word_activity_np - pm.min_activity) * pm.decay


        #-------------------------------------------------------------------------------------------------

            # # Enter the stimulus' word activities for the current cycle into all_data.
            # for word in xrange(len(stimulus.split(" "))-2):
            #     word_activity = lexicon_word_activity_np[lexicon_index_dict[stimulus.split(" ")[word+1]]]
            #     #word_activity = lexicon_word_activity[stimulus.split(" ")[word+1]]
            #     all_data[fixation_counter]['word activities per cycle'][word][stimulus.split(" ")[word+1]].append(word_activity)

            # Here, we check whether a shift will be made after the current cycle.
            # This can be due to the total activity threshold, or the recognition threshold.
            total_activity = 0
            for word in xrange(len(stimulus.split(" "))-2):
                total_activity += lexicon_word_activity_np[lexicon_index_dict[stimulus.split(" ")[word+1]]]

            crt_fixation_word_activities[3]=lexicon_word_activity_np[lexicon_index_dict[individual_words[fixation]]]
            crt_fixation_word_activities[4]=total_activity
            crt_fixation_word_activities_np[amount_of_cycles,3] = lexicon_word_activity_np[lexicon_index_dict[individual_words[fixation]]]
            crt_fixation_word_activities_np[0,4] = word_thresh_dict[individual_words[fixation]]
            all_data[fixation_counter]['fixation word activities'].append(crt_fixation_word_activities)
            all_data[fixation_counter]['fixation word activities np'] = crt_fixation_word_activities_np

            # ## lower threshold for predictable N+1 words to prevent premature allocation (i.e. prevent errors)
            # if shift and fixation < TOTAL_WORDS-1:
            #     lexicon_next_word = individual_to_lexicon_indices[fixation+1]
            #     norm_pred_next_word = normalize_pred_values(pm.wordpred_p,word_pred_values[fixation+1])
            #     lexicon_thresholds_np[lexicon_next_word] = lexicon_thresholds_np[lexicon_next_word] * norm_pred_next_word

            ## Enter any recognized word to the 'recognized words indices' list for the current fixation.
            recognized_lexicon_np = np.where(lexicon_word_activity_np>lexicon_thresholds_np)[0]
            #todo can maybe be faster, not from all_data
            recognized_indices = np.asarray(all_data[fixation_counter]['recognized words indices'], dtype=int)
            already_recognized_words_selection = np.in1d(recognized_lexicon_np,recognized_indices)
            new_recognized_words = recognized_lexicon_np[~already_recognized_words_selection]
            alldata_recognized_append = all_data[fixation_counter]['recognized words indices'].append
            allocated_append = allocated_dict[fixation].append
            alldata_truerecognized_append = all_data[fixation_counter]['exact recognized words positions'].append

            for word in new_recognized_words:
                my_print('recognized: ',amount_of_cycles,'cycle,',lexicon[word],lexicon_word_activity_np[word]/lexicon_thresholds_np[word],'(ratio crt. activity to threshold)')
                alldata_recognized_append(word)
                # if yes, words are considered recognized based on similarity of word lengths
                # otherwise, words are considered recognized only if they match exactly
                # TODO think about regressions, should N be excluded from N-1 when regressed?
                if pm.similarity_based_recognition:
                    # set the recognition flag to any of the words in a similar if they fulfill the word length distance condition
                    if is_similar_word_length(individual_words[fixation],lexicon[word]):
                        # todo refixations cause problems, because might be that during refix N+1 is recognized before N
                        # maybe just exclude the word during refixation
                        #not N-2, N-1,
                        if word not in already_allocated and not all_data[fixation_counter]['refixated']:
                            if not recognized_position_flag[fixation] or (amount_of_cycles < 1 and not len(allocated_dict[fixation])):
                                allocated_append(word)
                            recognized_position_flag[fixation] = True
                            #todo remove last appended before actual saccade, maybe == N+1
                            my_print(('+++ 0',lexicon[word],' recognized instead ',individual_words[fixation]))
                    elif shift and fixation+1 < TOTAL_WORDS and is_similar_word_length(individual_words[fixation+1],lexicon[word]):
                        #not N-2, N-1, N
                        if word not in already_allocated:
                            recognized_position_flag[fixation+1] = True
                            my_print(('+++ +1',lexicon[word],' recognized instead ',individual_words[fixation+1]))
                    if fixation-1 >= 0 and is_similar_word_length(individual_words[fixation-1],lexicon[word]):
                        if word not in allocated_dict[fixation-2]:
                            recognized_position_flag[fixation-1] = True
                            my_print(('+++ -1',lexicon[word],' recognized instead ',individual_words[fixation-1]))
                    #TODO solve issue of N and N+2/N-2 same length, N+2 already recognized at N fixation for longer words
                    # if fixation+2 < TOTAL_WORDS and is_similar_word_length(individual_words[fixation+2],lexicon[word]):
                    #     recognized_position_flag[fixation+2] = True
                        # print('+++',lexicon[word],' recognized instead ',individual_words[fixation+2])
                    # if fixation-2 >= 0 and is_similar_word_length(individual_words[fixation-2],lexicon[word]):
                    #     recognized_position_flag[fixation-2] = True
                    #     # print('+++',lexicon[word],' recognized instead ',individual_words[fixation-2])

                    ## TODO make vector comparison
                    # set the recognition flag for when the exact word is recognized (and store its position in the stimulus)
                    # this is also used later to check which words were not recognized
                    if individual_to_lexicon_indices[fixation] == word:
                        alldata_truerecognized_append(fixation)
                        recognized_word_at_position_flag[fixation] = True
                        #assert(individual_words[fixation] == lexicon[word])
                    elif(fixation+1<TOTAL_WORDS and individual_to_lexicon_indices[fixation+1] == word):
                        alldata_truerecognized_append(fixation+1)
                        recognized_word_at_position_flag[fixation+1] = True
                        #assert(individual_words[fixation+1] == lexicon[word])
                    elif(fixation-1>=0 and individual_to_lexicon_indices[fixation-1] == word):
                        alldata_truerecognized_append(fixation-1)
                        recognized_word_at_position_flag[fixation-1] = True
                        #assert(individual_words[fixation-1] == lexicon[word])
                    # elif(fixation-2>=0 and individual_to_lexicon_indices[fixation-2]==word):
                    #     alldata_truerecognized_append(fixation-2)
                    #     recognized_word_at_position_flag[fixation-2] = True
                    # elif(fixation+2<TOTAL_WORDS and individual_to_lexicon_indices[fixation+2] == word):
                    #     alldata_truerecognized_append(fixation+2)
                    #     recognized_word_at_position_flag[fixation] = True
                    #     #assert(individual_words[fixation+2] == lexicon[word])
                    else:
                    #use -1 to represent words that are not in the vicinity
                        alldata_truerecognized_append(-1)
                else:
                    sys.exit("No dissimilar length recognition")

        #-------------------------------------------------------------------------------------------------
            ## Word selection and Attentional shift

            if shift == False:
                distribution_type_recognized = False
                if recognized_position_flag[fixation]:
                    shift_start = norm_distribution(pm.mu, pm.sigma, pm.distribution_param, recognized=True)
                    distribution_type_recognized = True
                    # create longer fixations for before pred words
                    if attendposition_change:
                        shift_start = shift_start + width_change_delay
                else:
                    shift_start = norm_distribution(pm.mu, pm.sigma, pm.distribution_param, recognized=False)

                if amount_of_cycles >= shift_start:
                    shift = True

                    word_attention_right = calc_word_attention_right(rightWordEdgeLetterIndexes, EyePosition, AttentionPosition, attendWidth, recognized_position_flag, fixation, salience_position_new)
                    my_print("Word attention right:",word_attention_right)

                    # Reset attentional width
                    if attendposition_change:
                        my_print("attentional width delay:", attendposition_change_counter,salience_position_new)
                        # attendWidth = attendWidth_reset
                        salience_position_new = pm.salience_position
                        attendposition_change = False

                    # Attention will shift, so the new attention position (and thus future eye position) is calculated here.
                    my_print("distribution recognition:", distribution_type_recognized,shift_start,"Cycles:", amount_of_cycles)

                    #At the end of a regression, go forward 1 or two positions
                    if all_data[fixation_counter]['regressed']==True:  # If the current fixation was a regression, the eyes may need to go to word n+2 to resume reading.
                        #if individual_words[fixation+1] in all_data[fixation_counter]['recognized words']:
                        if lexicon_index_dict[individual_words[fixation+1]] in all_data[fixation_counter]['recognized words indices']:
                            #go forward two words
                            AttentionPosition = getMidwordPositionForSurroundingWord(2,rightWordEdgeLetterIndexes,leftWordEdgeLetterIndexes)
                            OffsetFromWordCenter=0
                            wordskip = True #TODO is not a firstpass wordskip
                            wordskip_pass = 2
                        else:
                            #go forward one word
                            AttentionPosition = getMidwordPositionForSurroundingWord(1,rightWordEdgeLetterIndexes,leftWordEdgeLetterIndexes)
                            OffsetFromWordCenter=0
                            forward = True
                        regression = False

                    # Check whether the previous word was recognized or there was already a regression performed. If not: regress.
                    elif fixation>1 and recognized_position_flag[fixation-1] == False and regression_flag[fixation-1]==False:
                            AttentionPosition = getMidwordPositionForSurroundingWord(-1,rightWordEdgeLetterIndexes,leftWordEdgeLetterIndexes)
                            OffsetFromWordCenter=0
                            regression = True

                    #elif (not recognized_position_flag[fixation]) and (lexicon_word_activity[individual_words[fixation]]>0):
                    elif (not recognized_position_flag[fixation]) and (lexicon_word_activity_np[lexicon_index_dict[individual_words[fixation]]]>0):
                        # Refixate if the foveal word is not recognized but is still being processed. This is not the
                        # case if after the last cycle its activity is still 0 for some reason; In case the word has
                        # activity 0 after 12 cycles, there is no use in fixating on it longer.

                        #TODO error in word_reminder_length, ->solved using +1 in refixsize?
                        word_reminder_length = rightWordEdgeLetterIndexes[0][1]-(rightWordEdgeLetterIndexes[0][0])
                        if(word_reminder_length>0):
                            #Use first refixation middle of remaining half as refixation stepsize
                            if all_data[fixation_counter-1]['refixated'] !=True:
                                refixsize = round((word_reminder_length)*pm.refix_size)
                                AttentionPosition = fixationFirstPositionRightToMiddle + refixsize
                            else:
                                AttentionPosition = fixationFirstPositionRightToMiddle + refixsize
                            OffsetFromWordCenter = (AttentionPosition - fixationCenter)
                            refixation = True
                            refixation_type = 1
                            my_print("Refixation not recognized",refixsize,OffsetFromWordCenter,word_reminder_length)

                        elif fixation<(TOTAL_WORDS-1):
                            #jump to the middle of the next word
                            AttentionPosition = getMidwordPositionForSurroundingWord(1,rightWordEdgeLetterIndexes,leftWordEdgeLetterIndexes)
                            OffsetFromWordCenter=0
                            forward = True

                    #perform normal forward saccade (unless at the last position in the text)
                    elif fixation<(TOTAL_WORDS-1):
                        # Wordskip on basis of activation, not if already recognised
                        # May cause problem, because recognition is scaled using threshold (length/frequency) but activation is not
                        # Because +1 word is already recognised, +2 is not, but still moves to +1 due to higher activity
                        indexOfMax = word_attention_right.index(max(word_attention_right))
                        nextFixation = indexOfMax

                        word_reminder_length = rightWordEdgeLetterIndexes[0][1]-(rightWordEdgeLetterIndexes[0][0])
                        if nextFixation == 0:
                            #Use first refixation middle of remaining half as refixation stepsize
                            if all_data[fixation_counter-1]['refixated'] !=True:
                                refixsize = round((word_reminder_length)*pm.refix_size)
                                AttentionPosition = fixationFirstPositionRightToMiddle + refixsize
                            else:
                                AttentionPosition = fixationFirstPositionRightToMiddle + refixsize
                            OffsetFromWordCenter = (AttentionPosition - fixationCenter)
                            refixation = True
                            refixation_type = 2
                            my_print("Refixation by Activity",refixsize,OffsetFromWordCenter, word_reminder_length)
                        else:
                            assert(nextFixation in [1,2])
                            AttentionPosition = getMidwordPositionForSurroundingWord(nextFixation,rightWordEdgeLetterIndexes,leftWordEdgeLetterIndexes)
                            OffsetFromWordCenter=0
                            if nextFixation==1:
                                forward = True
                            if nextFixation==2:
                                wordskip=True
                                wordskip_pass = 1

                    saccade_distance = AttentionPosition - EyePosition

            ## make sure outside "if shift == False statement"
            if shift == True: # count the amount of cycles since attention shift.
                if amount_of_cycles_since_attention_shifted < 1:
                    crt_fixation_word_activities_atshift = crt_fixation_word_activities
                    if (fixation+1 <= TOTAL_WORDS-1) and (fixation-1 > 0):
                        #stimulus_competition = individual_to_lexicon_indices[np.array([fixation-1, fixation+1])]
                        stimulus_competition = individual_to_lexicon_indices[np.array([fixation+1])]
                        fixated_word = individual_to_lexicon_indices[fixation]
                        competition_atshift = np.dot(lexicon_word_activity_np[stimulus_competition],word_overlap_matrix[fixated_word,stimulus_competition])
                        competition_overlap = np.sum(word_overlap_matrix[fixated_word,stimulus_competition])
                        all_data[fixation_counter]['stimulus competition'] = competition_overlap
                        all_data[fixation_counter]['stimulus competition2'] = competition_atshift

                    if fixation+1 < (TOTAL_WORDS-1):
                        lexicon_word_index = lexicon_index_dict[individual_words[fixation+1]]
                        my_print("n+1 word:",lexicon_word_activity_np[lexicon_word_index]/lexicon_thresholds_np[lexicon_word_index])
                amount_of_cycles_since_attention_shifted += 1


            if recognized_word_at_position_flag[fixation] == True and recognized_word_at_cycle[fixation]==-1:
                recognized_word_at_cycle[fixation] = amount_of_cycles

            # Make sure that attention is integer
            AttentionPosition = round(AttentionPosition)
            amount_of_cycles += 1
                
    # ----------------------------End of cycle--------------------------------------------------

        # After the last cycle, the fixation duration can be calculated.
        fixation_duration = amount_of_cycles * CYCLE_SIZE
#        if fixation in target_positions:
#            print 'NOW \n'
#            if len(target_words)>0:
#                if [individual_words[fixation],fixation] == target_words[-1]:
#                    target_word_refixs[-1] = 1
#                    target_word_gd[-1] += fixation_duration
#                else:
#                    target_words.append([individual_words[fixation],fixation])
#                    target_word_gd.append(fixation_duration)
#                    target_word_sf.append(fixation_duration)
#                    target_word_refixs.append(0)
#                    target_word_act.append(crt_fixation_word_activities_atshift[3])
#            else:
#                target_words.append([individual_words[fixation],fixation])
#                target_word_gd.append(fixation_duration)
#                target_word_sf.append(fixation_duration)
#                target_word_refixs.append(0)
#                target_word_act.append(crt_fixation_word_activities_atshift[3])
            

        all_data[fixation_counter]['fixation duration'] = fixation_duration
        all_data[fixation_counter]['recognition cycle'] = recognized_word_at_cycle[fixation]
        all_data[fixation_counter]['word threshold'] = word_thresh_dict[individual_words[fixation]]
        all_data[fixation_counter]['word excitation']  = crt_fixation_word_activities_atshift[0]
        all_data[fixation_counter]['bigram inhibition']  = crt_fixation_word_activities_atshift[1]
        all_data[fixation_counter]['between word inhibition']  = crt_fixation_word_activities_atshift[2]
        all_data[fixation_counter]['word activity']  = crt_fixation_word_activities_atshift[3]
        all_data[fixation_counter]['total activity']  = crt_fixation_word_activities_atshift[4]
        try:
            all_data[fixation_counter]['word frequency'] = word_freq_dict[individual_words[fixation]]
        except KeyError:
            all_data[fixation_counter]['word frequency'] = 0
        all_data[fixation_counter]['word predictability'] = word_pred_values[fixation]


        my_print("Relative Activity", crt_fixation_word_activities_atshift[3]/word_thresh_dict[individual_words[fixation]])
        my_print("Fixation duration: ", amount_of_cycles * CYCLE_SIZE, " ms.")
        #--------------------------------------------------------------------------------------

        if pm.visualise:
            Visualise_reading.update_stimulus(stimulus,EyePosition,attendWidth,AttentionPosition,fixation)
            Visualise_reading.main()
            Visualise_reading.save_screen(fixation_counter,"shift")

        if fixation == TOTAL_WORDS-1:  # Check if end of text is reached.
            end_of_text = True
            print("END REACHED!")
            continue

        my_print(regression,refixation,forward,wordskip)
        my_print("Recognized flag:", recognized_position_flag[fixation])

        # Prevent errors in offset calculation
        if not refixation:
            assert(OffsetFromWordCenter==0)

        ## Normal random error based on difference with optimal saccade distance
        saccade_error = calc_saccade_error(saccade_distance,pm.sacc_optimal_distance,pm.saccErr_scaler,pm.saccErr_sigma,pm.saccErr_sigma_scaler)
        saccade_distance = saccade_distance + saccade_error
        OffsetFromWordCenter = OffsetFromWordCenter + saccade_error

        ## Below, the position of the next fixation is calculated
        nextEyePosition = int(round(EyePosition+saccade_distance))
        if nextEyePosition >= len(stimulus)-1:
            nextEyePosition = len(stimulus)-2
            assert(rightWordEdgeLetterIndexes[-1][1] == len(stimulus)-2)

        my_print("nextEyePosition intended:",nextEyePosition,AttentionPosition,saccade_error, "indices R:",rightWordEdgeLetterIndexes)

        # ## Check eyepos not too far outside stimulus, due to error
        # if fixation < TOTAL_WORDS-2:
        #     assert(nextEyePosition <= rightWordEdgeLetterIndexes[-1][1]+2) # eyepos > Max eyepos, need to lower saccade error sigma

        ## Calculating the actual saccade type
        saccade_type_by_error = 0 # 0:no error, 1:refixation, 2:forward, 3:wordskip by error

        #regressions
        if nextEyePosition < centerWordFirstLetterIndex:
            #Eye at right space position
            if nextEyePosition > leftWordEdgeLetterIndexes[-2][1]:
                OffsetFromWordCenter-=1
            #Eyepos < N-1
            if nextEyePosition < leftWordEdgeLetterIndexes[-2][0]:
                centerposition_r = getMidwordPositionForSurroundingWord(-1,rightWordEdgeLetterIndexes,leftWordEdgeLetterIndexes)
                OffsetFromWordCenter = centerposition_r - leftWordEdgeLetterIndexes[-2][0]
            fixation-=1
            regression = True
            refixation, wordskip, forward = False, False, False
            my_print("<-<-<-<-<-<-<-<-<-<-<-<-")

        #Forward (include space between n and n+2)
        elif ((fixation < TOTAL_WORDS-1) and (nextEyePosition > centerWordLastLetterIndex) and (nextEyePosition <= (rightWordEdgeLetterIndexes[1][1]))):
            #When saccade too short due to saccade error recalculate offset for n+1 (old ofsett is for N or N+2)
            if wordskip or refixation:
                centerposition = getMidwordPositionForSurroundingWord(1,rightWordEdgeLetterIndexes,leftWordEdgeLetterIndexes)
                OffsetFromWordCenter = nextEyePosition - centerposition
                saccade_type_by_error = 2
                my_print("Forward by error",centerposition,nextEyePosition,OffsetFromWordCenter)
            #Eye at (n+0 <-> n+1) space position
            if nextEyePosition < rightWordEdgeLetterIndexes[1][0]:
                OffsetFromWordCenter+=1
            fixation += 1
            forward = True
            regression, refixation, wordskip = False, False, False
            my_print(">->->->->->->->->->->->-")

        #Wordskip
        elif ((fixation < TOTAL_WORDS-2) and (nextEyePosition > rightWordEdgeLetterIndexes[1][1]) and (nextEyePosition <= rightWordEdgeLetterIndexes[2][1]+2) ):
            if forward or refixation:
                #recalculate offset for n+2, todo check for errors
                centerposition = getMidwordPositionForSurroundingWord(2,rightWordEdgeLetterIndexes,leftWordEdgeLetterIndexes)
                OffsetFromWordCenter = nextEyePosition - centerposition
                saccade_type_by_error = 3
                my_print("Wordskip by error", nextEyePosition, saccade_distance, saccade_error)
            #Eye at (n+1 <-> n+2) space position
            if nextEyePosition < rightWordEdgeLetterIndexes[2][0]:
                OffsetFromWordCenter+=1
            #Eye at (> n+2) space position
            elif nextEyePosition > rightWordEdgeLetterIndexes[2][1]:
                OffsetFromWordCenter-= (nextEyePosition-rightWordEdgeLetterIndexes[2][1])
            fixation += 2
            wordskip = True
            regression, refixation, forward = False, False, False
            my_print(">>>>>>>>>>>>>>>>>>>>>>>>")

        #Refixation
        else:
            my_print("Refixation indended:",refixation,OffsetFromWordCenter)
            # Refixation due to saccade error
            if not refixation:
                #TODO find out if not regression is necessary
                centerposition = round(centerWordFirstLetterIndex + ((centerWordLastLetterIndex - centerWordFirstLetterIndex)/2.))
                OffsetFromWordCenter = nextEyePosition - centerposition
                saccade_type_by_error = 1
                refixation_type = 3
                my_print("Refixation by error:",nextEyePosition, saccade_distance, saccade_error,OffsetFromWordCenter,regression)
            refixation = True
            regression, wordskip, forward = False, False, False
            my_print("------------------------")

        if fixation+1 < (TOTAL_WORDS-1):
            lexicon_word_index = lexicon_index_dict[individual_words[fixation+1]]
            my_print("n+1 word atsacc:",lexicon_word_activity_np[lexicon_word_index]/lexicon_thresholds_np[lexicon_word_index])
        fixation_counter+=1
        #print "nextEyePosition Final:",OffsetFromWordCenter,stimulus[nextEyePosition:(nextEyePosition+4)]

        ## stop if nexteyeposition is at (last letter -1) of text, to prevent errors
        if fixation == TOTAL_WORDS-1 and nextEyePosition >= len(stimulus)-3:
            end_of_text = True
            continue
        my_print(regression,refixation,forward,wordskip)


    # append unrecognized words to the list
    unrecognized_words = []
    unrecognized_words_append = unrecognized_words.append
    for position in xrange(TOTAL_WORDS):
        if not recognized_word_at_position_flag[position]:
            unrecognized_words_append((individual_words[position],position))
    #-----------------------------------------------------------------------------------------------------

    # END OF READING. Return all_data and the list of unrecognized words.
    print N_in_allocated,N1_in_allocated
#    print target_words
#    
#    with open("C:\\Users\\Josh\\Desktop\\josh work\\Experiments\\BOB\\sam reading model july15\\sam reading model july15\\PSC\\newrep.txt", "w") as g:
#       g.write('condition,SF,GD,refix,activity\n') 
#       for i in range(0,len(target_words)):
#           g.write(target_words[i][0]+',0,'+str(target_word_sf[i])+','+str(target_word_gd[i])+','+str(target_word_refixs[i])+','+str(target_word_act[i])+'\n')
#    g.close()    
    
    
    return (lexicon,all_data, unrecognized_words)

#---------------------------------------------------------------------------------

#reading_simulation('C:/Users/SAM/PycharmProjects/StageVu/PSC/PSCshort3.txt')
