# -*- coding: utf-8 -*-

#    Copyright (C) 2011  Bartosz Wesołowski
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import Counter, defaultdict
from optparse import OptionParser
import codecs
import json
import os.path
import random
import re
import sys

RHYMES_FILE_NAME = os.path.join('data', 'rhymes.json')
BEFORE_WORDS_FILE_NAME = os.path.join('data', 'beforewords.json')
PROPER_NAMES_FILE_NAME = os.path.join('data', 'propernames.json')

CHARACTERS_TO_REMOVE = ',-—–„”«»*/[]1234567890'
SENTENCE_SEPARATORS = '.!?…;:()'

ROMAN_PATTERN_1 = re.compile('^[IVX]+$', re.MULTILINE)
ROMAN_PATTERN_2 = re.compile('^.* [IVX]+$', re.MULTILINE)

def removeTitleAndAuthorInformation(text):
    index = text.find('\n\n\n') + 3
    return text[index:]

def removeFootnote(text):
    index = text.rfind('\n\n\n\n')
    return text[:index]

def getText(filePath):
    f = codecs.open(filePath, 'r', 'utf-8')
    lines = f.readlines()
    text = "".join(lines)
    text = removeTitleAndAuthorInformation(text)
    text = removeFootnote(text)
    return text

def removeLinesWithRomanNumbers(text):
    while(re.search(ROMAN_PATTERN_1, text)):
        text = re.sub(ROMAN_PATTERN_1, '', text)
    while(re.search(ROMAN_PATTERN_2, text)):
        text = re.sub(ROMAN_PATTERN_2, '', text)
    return text

def removeCharacters(s, characters):
    result = s
    for c in characters:
        result = result.replace(c, '')
    return result

def splitIntoSentences(text):
    pattern = re.compile('[' + SENTENCE_SEPARATORS + ']')
    return re.split(pattern, text)

def updateBeforeWords(beforeWords, text):
    textLower = text.lower()
    sentences = splitIntoSentences(textLower)
    for sentence in sentences:
        previousWord = None
        for word in sentence.split():
            if (previousWord != None):
                beforeWords[word][previousWord] += 1
            previousWord = word
        
def wordsRhyme(word1, word2):
    a = word1.replace('ó', 'u')
    a = a.replace('rz', 'ż')
    a = a.replace('ch', 'h')
    b = word2.replace('ó', 'u')
    b = b.replace('rz', 'ż')
    b = b.replace('ch', 'h')
    return a[-3:] == b[-3:]

def transitiveSymmetricAdd(rhymes, word1, word2):
    rhymes1 = set(rhymes[word1])
    rhymes2 = set(rhymes[word2])
    
    for word in rhymes1:
        rhymes[word].update(rhymes2)
        rhymes[word].add(word2)
            
    for word in rhymes2:
        rhymes[word].update(rhymes1)
        rhymes[word].add(word1)
    
    rhymes[word1].update(rhymes2)
    rhymes[word1].add(word2)
    rhymes[word2].update(rhymes1)
    rhymes[word2].add(word1)
        
def findRhymes(rhymes, text):
    lowerText = text.lower()
    lines = lowerText.splitlines()
    wordsInLines = []
    for line in lines:
        wordsInLine = line.split()
        if (len(wordsInLine) != 0):
            wordsInLines.append(wordsInLine)
    lastWords = [wordsInLine[-1] for wordsInLine in wordsInLines]
    for i in range(0, len(lastWords) - 1):
        word1 = lastWords[i]
        for j in range(i + 1, min(i + 4, len(lastWords))):
            word2 = lastWords[j]
            if not word1 == word2 and wordsRhyme(word1, word2) and not word2 in rhymes[word1]:
                transitiveSymmetricAdd(rhymes, word1, word2)
                
def findProperNames(properNames, ordinaryWords, text):
    sentences = splitIntoSentences(text)
    firstWordsInSentence = set()
    for sentence in sentences:
        words = sentence.split()
        if words:
            firstWordsInSentence.add(words[0])
    cleanText = removeCharacters(text, SENTENCE_SEPARATORS)
    lines = cleanText.splitlines()
    firstWordsInLine = set()
    for line in lines:
        words = line.split()
        if words:
            firstWordsInLine.add(words[0])
    words = cleanText.split()
    for word in words:
        if word[0].isupper() and not word in firstWordsInLine and not word in firstWordsInSentence:
            properNames.add(word)
        if word[0].islower():
            ordinaryWords.add(word)
                
def numSyllablesOnList(l):
    return numSyllables(" ".join(l))               
                
def numSyllables(text):
    count = text.count('a')
    count += text.count('ą')
    count += text.count('e')
    count += text.count('ę')
    count += text.count('i')
    count += text.count('o')
    count += text.count('ó')
    count += text.count('u')
    count += text.count('y')
    count -= text.count('au')
    count -= text.count('eu')
    count -= text.count('ia')
    count -= text.count('ie')
    count -= text.count('ią')
    count -= text.count('ię')
    return count
                
def createLine(syllables, beforeWords, line):
    s = numSyllablesOnList(line)
    if s == syllables:
        line[0] = line[0].capitalize()
        return line
    if s > syllables: return None
    
    possibleWords = beforeWords[line[0]]
    if not possibleWords: return None
    possibleWordsLeft = set(possibleWords)
    word = random.choice(list(possibleWordsLeft))
    possibleWordsLeft.remove(word)
    newline = createLine(syllables, beforeWords, [word] + line)
    while not newline and possibleWordsLeft:
        word = random.choice(list(possibleWordsLeft))
        possibleWordsLeft.remove(word)
        newline = createLine(syllables, beforeWords, [word] + line)
    return newline

def createLineWithLastWord(syllables, beforeWords, lastWord):
    return createLine(syllables, beforeWords, [lastWord])
                
def createVerse(beforeWords, rhymes, rhymePattern, syllablePattern):
    lines = []
    
    for lineNumber in range(0, len(rhymePattern)):
        rhymePatternSymbol = rhymePattern[lineNumber]
        rhymingWord = None
        for i in range(lineNumber - 1, -1, -1):
            if rhymePattern[i] == rhymePatternSymbol:
                rhymingWord = lines[i][-1]
                break
            
        possibleLines = []
        if rhymingWord:
            for lastWord in rhymes[rhymingWord]:
                l = createLineWithLastWord(syllablePattern[lineNumber], beforeWords, lastWord)
                if l: possibleLines.append(l)
        else:
            for lastWord in random.sample(list(rhymes.keys()), 10):
                l = createLineWithLastWord(syllablePattern[lineNumber], beforeWords, lastWord)
                if l: possibleLines.append(l)
            
        line = None
        if possibleLines:
            line = random.choice(possibleLines)
        else:
            return createVerse(beforeWords, rhymes, rhymePattern, syllablePattern)
        
        lines.append(line)
        
    text = ''
    for line in lines:  
        text += ' '.join(line)
        text += '\n'
    
    return text

def createPoem(numVerses, rymePattern, syllablePattern):
    verses = []
    for _ in range(numVerses):
        verses.append(createVerse(beforeWords, rhymes, rhymePattern, syllablePattern))
    poem = '\n'.join(verses)
    words = poem.split()
    for word in words:
        if word.capitalize() in properNames:
            pattern = re.compile('\\b' + word + '\\b', re.MULTILINE)
            poem = re.sub(pattern, word.capitalize(), poem)
    return poem

def saveRhymes(rhymes):
    if not os.path.exists('data'):
        os.mkdir('data')
    f = open(RHYMES_FILE_NAME, 'w')
    simpleRhymes = dict()
    for word in rhymes.keys():
        simpleRhymes[word] = list(sorted(rhymes[word]))
    json.dump(simpleRhymes, f, indent=10)
    f.close()
    
def loadRhymes():
    f = open(RHYMES_FILE_NAME, 'r')
    simpleRhymes = json.load(f)
    rhymes = defaultdict(set)
    for word in simpleRhymes.keys():
        rhymes[word] = set(simpleRhymes[word])
    f.close()
    return rhymes

def saveBeforeWords(beforeWords):
    if not os.path.exists('data'):
        os.mkdir('data')
    f = open(BEFORE_WORDS_FILE_NAME, 'w')
    simpleBeforeWords = dict()
    for word in beforeWords.keys():
        simpleBeforeWords[word] = list(sorted(beforeWords[word]))
    json.dump(simpleBeforeWords, f, indent=10)
    f.close()

def loadBeforeWords():
    f = open(BEFORE_WORDS_FILE_NAME, 'r')
    simpleBeforeWords = json.load(f)
    beforeWords = defaultdict(Counter)
    for word in simpleBeforeWords.keys():
        beforeWords[word] = set(simpleBeforeWords[word])
    f.close()
    return beforeWords

def saveProperNames(properNames):
    if not os.path.exists('data'):
        os.mkdir('data')
    f = open(PROPER_NAMES_FILE_NAME, 'w')
    simpleProperNames = list(sorted(properNames))
    json.dump(simpleProperNames, f, indent=10)
    f.close()

def loadProperNames():
    f = open(PROPER_NAMES_FILE_NAME, 'r')
    simpleProperNames = json.load(f)
    properNames = set(simpleProperNames)
    f.close()
    return properNames

def getAssets():
    rhymes = defaultdict(set)
    beforeWords = defaultdict(Counter)
    properNames = set()
    ordinaryWords = set()
    
    rhymesFileExists = os.path.exists(RHYMES_FILE_NAME)
    beforeWordsFileExists = os.path.exists(BEFORE_WORDS_FILE_NAME);
    properNamesFileExists = os.path.exists(PROPER_NAMES_FILE_NAME);
            
    if rhymesFileExists:
        rhymes = loadRhymes()
    if beforeWordsFileExists:
        beforeWords = loadBeforeWords()
    if properNamesFileExists:
        properNames = loadProperNames()
    
    if not rhymesFileExists or not beforeWordsFileExists or not properNames:
        if not os.path.exists('txt-liryka'):
            print('"txt-liryka" folder not found')
        else:
            for dirPath, _, fileNames in os.walk('txt-liryka'):
                for fileName in fileNames:
                    filePath = os.path.join(dirPath, fileName)
                    text = getText(filePath)
                    text = removeLinesWithRomanNumbers(text)
                    text = removeCharacters(text, CHARACTERS_TO_REMOVE)
                    if not beforeWordsFileExists:
                        updateBeforeWords(beforeWords, text)
                    if not properNamesFileExists:
                        findProperNames(properNames, ordinaryWords, text)
                    if not rhymesFileExists:
                        text = removeCharacters(text, SENTENCE_SEPARATORS)
                        findRhymes(rhymes, text)
            if (not rhymesFileExists or forceAssets) and saveAssets:
                saveRhymes(rhymes)
            if (not beforeWordsFileExists or forceAssets) and saveAssets:
                saveBeforeWords(beforeWords)
            properNames2 = set()
            for properName in properNames:
                ordinaryWord = properName.lower()
                if ordinaryWord not in ordinaryWords:
                    properNames2.add(properName)
            properNames = properNames2
            if (not properNamesFileExists or forceAssets) and saveAssets:
                saveProperNames(properNames)
            
    return (rhymes, beforeWords, properNames)

if __name__ == '__main__':
    parser = OptionParser(usage='usage: %prog [options]')
    parser.add_option('-v', '--verses', dest='verses', type='int', help='number of verses (default is 3)')
    parser.add_option("-r", "--rhyme_pattern", dest="rhymePattern", type='string', help="rhyme pattern e.g. ABAB (default)")
    parser.add_option("-s", "--syllable_pattern", dest="syllablePattern", type='string', help="number of syllables in each line of a verse, e.g 8,8,8,8")
    parser.add_option("-d", "--dont_save_assets", action="store_false", dest="saveAssets", default=True, help="do not create any files with assets (e.g. rhymes)")
    parser.add_option("-f", "--force_save_assets", action="store_true", dest="forceAssets", default=False, help="force overwrite of asset files")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False, help="do not print anything - prepare assets files if necessary")
    (options, args) = parser.parse_args()
    
    numVerses = 3
    if options.verses:
        if (options.verses >= 1):
            numVerses = options.verses
        else:
            print('Incorrect number of verses.')
            sys.exit(1)
    
    rhymePattern = 'ABAB'
    if options.rhymePattern:
        rhymePattern = options.rhymePattern
        
    syllablePatterns = ((8, 7, 8, 7), (11, 11, 11, 11), (8, 8, 8, 8))
    syllablePattern = random.choice(syllablePatterns)
    if options.syllablePattern:
        numbers = options.syllablePattern.split(',')
        try:
            syllablePattern = [int(n) for n in numbers]
        except:
            print('Incorrect syllable pattern.')
            sys.exit(1)
            
    quiet = options.quiet
    
    saveAssets = options.saveAssets
    
    forceAssets = options.forceAssets
    
    rhymes, beforeWords, properNames = getAssets()
    if rhymes and beforeWords and not quiet:
        print(createPoem(numVerses, rhymePattern, syllablePattern))
