from psychopy import core,gui

class Image:
    def __init__(self, name, categories):
        # Name is the image's file name (eg 'dog_1' from 'dog_1.jpg')
        self.name = name

        # Categories in descending specificity (eg ['Dog', 'Mammal', 'Living'])
        self.categories = categories

class ImportantCategory:
    def __init__(self, target, similar, remove):
        self.target = target
        self.similar = similar
        self.remove = remove

class Trial:
    def __init__(self, images):
        self.images = images

class Block:
    def __init__(self, targets, similars, randoms):
        self.targets = targets
        self.similars = similars
        self.randoms = randoms

class Experiment:
    def __init__(self, blocks, subject, questions, ):

class Subject:
    def __init__(self, id, target):
        self.id = id
        self.target = target

def create_subject(important_categories):
    important_categories_by_target = dict([(categ.target, categ) for categ in important_categories])
    expinfo = {'Subject ID': '', 'Target Category': important_categories_by_target.keys()}
    if not gui.DlgFromDict(expinfo, title='Subject Info').OK:
        core.quit()
    subj_id = expinfo['Subject ID']
    target = important_categories_by_target[expinfo['Target Category']]
    return Subject(subj_id, target)