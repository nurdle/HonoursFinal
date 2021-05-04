import nltk
from nltk.corpus import twitter_samples, stopwords
from nltk.tag import pos_tag
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import re, string, random
from nltk import FreqDist, classify, NaiveBayesClassifier
import pickle, os
import thinc
import spacy
import ctypes

#
# import cupy_cuda102

hllDll = ctypes.WinDLL("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v10.2/bin/cudart64_100.dll")


CUDA_PATH = "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v10.2\\bin"

spacy.prefer_gpu()
nlp = spacy.load("en_core_web_sm")

Stopwords = stopwords.words('english')
positive = twitter_samples.strings('positive_tweets.json')
negative = twitter_samples.strings('negative_tweets.json')
text = twitter_samples.strings('tweets.20150430-223406.json')
pos_tweet_tokens = twitter_samples.tokenized('positive_tweets.json')
neg_tweet_tokens = twitter_samples.tokenized('negative_tweets.json')

pos_cleaned, neg_cleaned = [], []

def lemmatizer(tokens):
    lemmatizer = WordNetLemmatizer()
    Result = []
    for word, tag in pos_tag(tokens):
        if tag.startswith("NN"):
            pos = 'n'
        elif tag.startswith("VB"):
            pos = 'v'
        else:
            pos = 'a'
        Result.append(lemmatizer.lemmatize(word, pos))
    return Result

def Noise_Remover(TweetTokens, StopWords =()):
    cleaned = []
    for token, tag in pos_tag(TweetTokens):
        token = re.sub('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+#]|[!*\(\),]|'\
                       '(?:%[0-9a-fA-F][0-9a-fA-F]))+','', token)
        token = re.sub("(@[A-Za-z0-9_]+)","", token)
        if tag.startswith("NN"):
            pos = 'n'
        elif tag.startswith("VB"):
            pos = 'v'
        else:
            pos = 'a'
        lemmatizer = WordNetLemmatizer()
        token = lemmatizer.lemmatize(token, pos)
        if len(token) > 0 and token not in string.punctuation and token.lower() not in StopWords:
            cleaned.append(token.lower())
    return cleaned

def get_word_list(cleaned_list):
    for tokens in cleaned_list:
        for token in tokens:
            yield token

def get_model_tweets(cleaned_list):
    for tokens in cleaned_list:
        yield dict([token, True] for token in tokens)

def mainTrain():
    for tokens in pos_tweet_tokens:
        pos_cleaned.append(Noise_Remover(tokens, Stopwords))

    for tokens in neg_tweet_tokens:
        neg_cleaned.append(Noise_Remover(tokens, Stopwords))

    all_pos_words = get_word_list(pos_cleaned)
    all_neg_words = get_word_list(neg_cleaned)
    pos_freq_dist = FreqDist(all_pos_words)
    neg_freq_dist = FreqDist(all_neg_words)
    pos_model_tokens = get_model_tweets(pos_cleaned)
    neg_model_tokens = get_model_tweets(neg_cleaned)

    pos_dataset = [(tweet_dict, "Positive") for tweet_dict in pos_model_tokens]
    neg_dataset = [(tweet_dict, "Negative") for tweet_dict in neg_model_tokens]

    dataset = pos_dataset + neg_dataset
    random.shuffle(dataset)

    train = dataset[:7000]
    test = dataset[7000:]

    classifier = NaiveBayesClassifier.train(train)
    print("Accuracy is:", classify.accuracy(classifier, test))

    print(classifier.show_most_informative_features(10))

    f = open("TweetClassifier.pickle", "wb")
    pickle.dump(classifier, f)
    f.close()
    return classifier

if os.path.isfile("TweetClassifier.pickle") == False:
   classifier = mainTrain()
else:
    f = open("TweetClassifier.pickle", "rb")
    classifier = pickle.load(f)
    f.close()

custom_tweet = "New China Virus Cases up (because of massive testing), deaths are down, ‘low and steady’. The Fake News Media should report this and also, that new job numbers are setting records!"
def AnalyseTweets(Tweets):
    ReturnSubjects = {}
    for tweet in Tweets:
        doc = nlp(tweet)
        PossibleSubjects = []
        for token in doc:
            if token.pos_ == "PROPN" or token.pos == "NOUN":
                print(token.text, ":", token.pos_)
                PossibleSubjects.append(token.text)
            print([child for child in token.children])
        print("Possible subjects of tweet: ", PossibleSubjects)
        custom_tokens = Noise_Remover(word_tokenize(tweet))
        classification = classifier.classify(dict([token, True] for token in custom_tokens))
        print("RESULT: " + classification)
        for i in range(len(PossibleSubjects)):
            if classification == "Negative":
                ReturnSubjects[str(PossibleSubjects[i])] = round(-1 * (1/(i+1)), 1)
            elif classification == "Positive":
                ReturnSubjects[str(PossibleSubjects[i])] = round(1 / (i+1), 1)
    return ReturnSubjects


##Output = AnalyseTweets(["New China Virus Cases up (because of massive testing), deaths are down, ‘low and steady’. The Fake News Media should report this and also, that new job numbers are setting records!"])
##print(Output)
if __name__ == "__main__":
    AnalyseTweets()