'''
Created on 2015-04-02

@author: Niranjan
'''

import re, math, collections, itertools, os
import nltk, nltk.classify.util, nltk.metrics
from nltk.classify import NaiveBayesClassifier
from nltk.metrics import BigramAssocMeasures
from nltk.probability import FreqDist, ConditionalFreqDist
from porter import PorterStemmer


DATA_DIR = 'data'
RT_POLARITY_POS_FILE = os.path.join(DATA_DIR, 'rt-polarity-pos.txt')
RT_POLARITY_NEG_FILE = os.path.join(DATA_DIR, 'rt-polarity-neg.txt')
stopwords=open('stopwords.txt','r').read().splitlines()
predictedfile=open("prediction.txt",'w')
Actualfile=open("actual.txt",'w')
stemmer=PorterStemmer()

#Takes a feature selection mechanism and returns its performance in a variety of metrics
def evaluate_features(feature_select):
        posFeatures = []
        negFeatures = []
        #breaks up the sentences into lists of individual words (as selected by the input mechanism) and appends 'pos' or 'neg' after each list
        pos1=open("positivewords1.txt",'w')
        neg1=open("negativewords1.txt",'w')
        with open(RT_POLARITY_POS_FILE, 'r') as posSentences:
                for i in posSentences:
                        posWords = re.findall(r"[\w']+|[.,!?;]", i.rstrip())
                        posWords=[x for x in posWords if not x in stopwords]
                        posWords=[x for x in posWords if len(x)>2]
                        posWords=[stemmer.stem(x,0,len(x)-1) for x in posWords]
                        pos1.write("\nWord:"+str(posWords))
                        posWords = [feature_select(posWords), 'pos']
                        posFeatures.append(posWords)
                        
        with open(RT_POLARITY_NEG_FILE, 'r') as negSentences:
                for i in negSentences:
                        negWords = re.findall(r"[\w']+|[.,!?;]", i.rstrip())
                        negWords=[x for x in negWords if not x in stopwords]
                        negWords=[x for x in negWords if len(x)>2]
                        negWords=[stemmer.stem(x,0,len(x)-1) for x in negWords]
                        neg1.write("\nWord:"+str(negWords))
                        negWords = [feature_select(negWords), 'neg']
                        negFeatures.append(negWords)
                        
        #selects 3/4 of the features to be used for training and 1/4 to be used for testing
        posCutoff = int(math.floor(len(posFeatures)*3/4))
        print("Positive train:"), posCutoff
        negCutoff = int(math.floor(len(negFeatures)*3/4))
        print("Negative train:"), negCutoff
        trainFeatures = posFeatures[:posCutoff] + negFeatures[:negCutoff]
        testFeatures = posFeatures[posCutoff:] + negFeatures[negCutoff:]

        #trains a Naive Bayes Classifier
        classifier = NaiveBayesClassifier.train(trainFeatures)  

        #initiates referenceSets and testSets
        referenceSets = collections.defaultdict(set)
        testSets = collections.defaultdict(set) 

        #puts correctly labeled sentences in referenceSets and the predictively labeled version in testsets
        for i, (features, label) in enumerate(testFeatures):
                referenceSets[label].add(i)
                predicted = classifier.classify(features)
                testSets[predicted].add(i)
        predictedfile.write("\n"+str(testSets))
        Actualfile.write("\n"+str(referenceSets))
        
        #prints metrics to show how well the feature selection did
        print 'train on %d instances, test on %d instances' % (len(trainFeatures), len(testFeatures))
        print 'accuracy:', nltk.classify.util.accuracy(classifier, testFeatures)
        print 'pos precision:', nltk.metrics.precision(referenceSets['pos'], testSets['pos'])
        print 'pos recall:', nltk.metrics.recall(referenceSets['pos'], testSets['pos'])
        print 'neg precision:', nltk.metrics.precision(referenceSets['neg'], testSets['neg'])
        print 'neg recall:', nltk.metrics.recall(referenceSets['neg'], testSets['neg'])
        classifier.show_most_informative_features(10)

#creates a feature selection mechanism that uses all words
def make_full_dict(words):
        return dict([(word, True) for word in words])

#tries using all words as the feature selection mechanism
print 'using all words as features'
evaluate_features(make_full_dict)

#scores words based on chi-squared test to show information gain
def create_word_scores():
        #creates lists of all positive and negative words
        posWords = []
        negWords = []
        with open(RT_POLARITY_POS_FILE, 'r') as posSentences:
                for i in posSentences:
                        posWord = re.findall(r"[\w']+|[.,!?;]", i.rstrip())
                        posWords.append(posWord)
        with open(RT_POLARITY_NEG_FILE, 'r') as negSentences:
                for i in negSentences:
                        negWord = re.findall(r"[\w']+|[.,!?;]", i.rstrip())
                        negWords.append(negWord)
        posWords = list(itertools.chain(*posWords))
        negWords = list(itertools.chain(*negWords))

        #build frequency distibution of all words and then frequency distributions of words within positive and negative labels
        word_fd = FreqDist()
        cond_word_fd = ConditionalFreqDist()
        for word in posWords:
                word_fd[word.lower()]+=1
                cond_word_fd['pos'][word.lower()]+=1
        for word in negWords:
                word_fd[word.lower()]+=1
                cond_word_fd['neg'][word.lower()]+=1

        #finds the number of positive and negative words, as well as the total number of words
        pos_word_count = cond_word_fd['pos'].N()
        neg_word_count = cond_word_fd['neg'].N()
        print("No. of Positive words are:"),pos_word_count
        print("No. of Negative words are:"),neg_word_count
        total_word_count = pos_word_count + neg_word_count

        #builds dictionary of word scores based on chi-squared test
        word_scores = {}
        for word, freq in word_fd.iteritems():
                pos_score = BigramAssocMeasures.chi_sq(cond_word_fd['pos'][word], (freq, pos_word_count), total_word_count)
                neg_score = BigramAssocMeasures.chi_sq(cond_word_fd['neg'][word], (freq, neg_word_count), total_word_count)
                word_scores[word] = pos_score + neg_score

        return word_scores

#finds word scores
word_scores = create_word_scores()

#finds the best 'number' words based on word scores
def find_best_words(word_scores, number):
        best_vals = sorted(word_scores.iteritems(), key=lambda (w, s): s, reverse=True)[:number]
        best_words = set([w for w, s in best_vals])
        return best_words

#creates feature selection mechanism that only uses best words
def best_word_features(words):
        return dict([(word, True) for word in words if word in best_words])

#numbers of features to select
numbers_to_test = [10, 100, 1000, 10000, 15000]
#tries the best_word_features mechanism with each of the numbers_to_test of features
for num in numbers_to_test:
        print '\nEvaluating best %d word features' % (num)
        best_words = find_best_words(word_scores, num)
        evaluate_features(best_word_features)
