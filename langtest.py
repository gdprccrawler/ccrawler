import langdetect
from yandex.Translater import Translater
from deep_translator import GoogleTranslator, PonsTranslator

def translate_words(language, word_list):
    translated_list = []
    tr = Translater
    for word in word_list:
        translated_word= GoogleTranslator(source="english", target=language).translate(word)
        translated_list.append(translated_word)
    print(translated_list)
    return translated_list



trigs = [       "ok",
                "i agree"]

translate_words("swedish",trigs)