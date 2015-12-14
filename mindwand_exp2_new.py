from psychopy import core, gui, visual
from random import choice, shuffle
import csv, fnmatch, os
import numpy as np
import pylinkwrapper

class Image:
    def __init__(self, name, categories, image_stim):
        # Name is the image's file name (eg 'dog_1' from 'dog_1.jpg')
        self.name = name

        # Categories in descending specificity (eg ['Dog', 'Mammal', 'Living'])
        self.categories = categories

        self.image_stim = image_stim

class ImportantCategory:
    def __init__(self, target, similar, remove):
        self.target = target
        self.similar = similar
        self.remove = remove

class Block:
    def __init__(self, targets, similars, randoms):
        self.targets = targets
        self.similars = similars
        self.randoms = randoms

    def generate_trials(self, images, important_category):
        trials = [] # empty trial list

        # Filters for target images at level 0
        all_target_images = filter(
            lambda image: image.categories[0] == important_category.target,
            images
        )

        all_similar_images = filter(
            lambda image: image.categories[0] == important_category.similar,
            images
        )

        def is_distractor(image):
            return (
                image.categories[0] != important_category.target and # Exclude target images
                image.categories[0] != important_category.remove # Exclude images from the 'remove' category
            )
        all_distractors = filter(is_distractor, images)

        distractors_by_level1 = {}
        #######
        # >>> desired = {
        # ...     'mammal': ['dog1', 'dog2', 'cat1', 'cat2'],
        # ...     'plant': ['fruit1', 'fruit2', 'tree1', 'tree2'],
        # ... }
        # >>> db = {}
        # >>> db
        # {}
        # >>> level1 = 'mammal'
        # >>> level1 not in db
        # True
        # >>> db[level1] = []
        # >>> db
        # {'mammal': []}
        # >>> db[level1].append('dog1')
        # >>> db
        # {'mammal': ['dog1']}
        # >>> level1 not in db
        # False
        # >>> db[level1].append('dog2')
        # >>> db
        # {'mammal': ['dog1', 'dog2']}
        #######
        for image in all_distractors:
            level1 = image.categories[1]
            if level1 not in distractors_by_level1: # Don't overwrite if the level1 is already there
                distractors_by_level1[level1] = [] # Initialize level1 to empty list
            distractors_by_level1[level1].append(image) # Add image to its level1 list

        for target_trial_num in range(self.targets): # Create 'self.targets' number of target trials
            trial_images = []
            trial_images.append(choice(all_target_images))
            trial_images.extend([
                choice(level1_images) # Choose a random images from the level1 images
                for level1_images in distractors_by_level1.values() # Go through all level1 categories
            ])
            while len(trial_images) < 10:
                distractor = choice(all_distractors)
                is_duplicate = False # Default to not a duplicate
                for image in trial_images:
                    if image.categories[0] == distractor.categories[0]:
                        is_duplicate = True

                if not is_duplicate: # Only add non-duplicates to the trial images
                    trial_images.append(distractor)

            trials.append(Trial(trial_images))

        for similar_trial_num in range(self.similars): # Create 'self.similars' number of similar trials
            trial_images = []
            trial_images.append(choice(all_target_images))
            trial_images.append(choice(all_similar_images))
            for level1_images in distractors_by_level1.values():
                level1_image = choice(level1_images)
                while level1_image.categories[0] == important_category.similar: # Check if similar category is chosen
                    level1_image = choice(level1_images) # Pick a new random one from the same level1
                trial_images.append(level1_image)

            while len(trial_images) < 10:
                distractor = choice(all_distractors)
                is_duplicate = False
                for image in trial_images:
                    if image.categories[0] == distractor.categories[0]:
                        is_duplicate = True

                if not is_duplicate:
                    trial_images.append(distractor)

            trials.append(Trial(trial_images))

        for random_trial_num in range(self.randoms): # Create 'self.randoms' number of random trials
            trial_images = []
            trial_images.extend([
                choice(level1_images) # Choose a random images from the level1 images
                for level1_images in distractors_by_level1.values() # Go through all level1 categories
            ])
            while len(trial_images) < 10:
                distractor = choice(all_distractors)
                is_duplicate = False
                for image in trial_images:
                    if image.categories[0] == distractor.categories[0]:
                        is_duplicate = True

                if not is_duplicate:
                    trial_images.append(distractor)

            trials.append(Trial(trial_images))

        shuffle(trials)
        return trials

class Experiment:
    def __init__(self, subject, questions, blocks, images):
        self.subject = subject
        self.questions = questions
        self.blocks = blocks
        self.images = images

    def ask_questions(self, window):
        question_responses = []
        for question, scale in self.questions:
            question_text = visual.TextStim(window, text=question, color=-1) # Question text
            scale_rating = visual.RatingScale(window, scale=scale, textColor=-1,
                                              lineColor=-1, noMouse=True) # Scale rating
            # Update until response
            while scale_rating.noResponse:
                question_text.draw()
                scale_rating.draw()
                window.flip()

            question_responses.append(scale_rating.getRating())
            scale_rating.reset()
        return question_responses

    def run(self, window, tracker, output_file):
        question_responses = self.ask_questions(window)

        # Stimuli
        fix = visual.Circle(window, radius=0.125, pos=(0, 0), fillColor=-1,
                            lineColor=-1)
        # Make Noise nots
        dots = visual.DotStim(window, coherence=0, fieldSize=(25, 15), color=-1,
                              nDots=10000)

        # TUT
        tut = TUTProbe(self.win)
        # Initiate TUTprop clock
        tuttime = core.Clock()
        tutgo = np.random.randint(15, 31)

        output_file.writerow([
            'sub'     # Subject id
            'tcateg'  # Target category
            'tar'     # If target was present
            'sim'     # If similar was present
            'resp'    #
            'rtype'   #
            'rt'      #
            'time'    #
            'tutra'   #
            'tuttime' #
            'hunger'  #
            'tired'   #
        ])
        for block_num, block in enumerate(self.blocks):
            for trial_num, trial in enumerate(block.generate_trials(self.images, self.subject.target)):
                # Randomize coordinates
                coords = [(x, y) for y in [-4, 0, 4] for x in np.linspace(-10, 10, 4)]
                del coords[5:7]
                coords = [xy + np.random.uniform(-.5, .5, 2) for xy in coords]

                # Check for fixation
                self.tracker.fixCheck(2, .1, 'z')

                # Pupil time
                self.tracker.setStatus('Pupil Time')
                self.tracker.setTrialID()
                self.tracker.drawIA(0, 0, 2, 1, 1, 'pfixation')
                self.tracker.sendMessage('pupiltime')
                fix.draw()
                self.tracker.recordON()
                self.win.flip()
                core.wait(1)
                self.tracker.recordOFF()
                self.tracker.setTrialResult()

                # Eye-tracker pre-stim
                statmsg = 'Experiment {}%% complete. Current Trial: {}'.format(round(trial['tnum'] / 300.0, 3) * 100, trial['tnum'])
                self.tracker.setStatus(statmsg)
                self.tracker.setTrialID()

                # Draw IAs
                self.tracker.drawIA(0, 0, 2, 1, 1, 'fixation')
                for csi, cs in enumerate(coords):
                    # set name
                    if images[csi] is target_stim_image:
                        name = 'target.%s' % images[csi]
                    elif images[csi] is similar_stim_image:
                        name = 'similar.%s' % images[csi]
                    else:
                        name = 'nonTarget.%s' % images[csi]

                    self.tracker.drawIA(cs[0], cs[1], 3, csi+2, csi+2, name)

class Subject:
    def __init__(self, id, target):
        self.id = id
        self.target = target

class Trial:
    def __init__(self, images):
        self.images = images

## TUT Probe
class TUTProbe:
    def __init__(self, win):
        self.win = win
        # Make scale
        rtxt = ('On the scale below, rate the duration of task unrelated thoughts '
                'since the last probe')
        self.rtxtob = visual.TextStim(self.win, text=rtxt, pos=(0, 3), height=1,
                                      color=-1)

        # Define rating scale
        sctxt = '0 = Not at all ... 5 = The whole time'
        self.ratingScale = visual.RatingScale(self.win, low=0, high=5, scale=sctxt,
                                              labels=map(str, range(6)),
                                              tickMarks=range(6), textColor=-1,
                                              lineColor=-1, noMouse=True)

    # Function for display
    def tutprobe(self):
        # Display and collect response
        while self.ratingScale.noResponse:
            self.rtxtob.draw()
            self.ratingScale.draw()
            self.win.flip()

        # Return and Reset
        rating = self.ratingScale.getRating()
        self.ratingScale.reset()
        return rating

def create_subject(important_categories):
    # Make a dictionary of target to category
    target_options = dict([(category.target, category) for category in important_categories])
    expinfo = {
        'Subject ID': '',
        'Target Category': target_options.keys() # Show options as target names
    }
    # Shows dialog box and quits experiment when cancel is clicked
    if not gui.DlgFromDict(expinfo, title='Subject Info').OK:
        core.quit()

    # Get the results from the dialog box
    id = expinfo['Subject ID']
    target_category_name = expinfo['Target Category']

    target = target_options[target_category_name] # Lookup the ImportantCategory for the target name
    return Subject(id, target)

def load_images(window, source_dir):
    visual.TextStim(window, 'Loading Images...', color=-1).draw() # Window that says Loading Images
    window.flip()

    # Find all the images files within source_dir
    image_files = [
            os.path.join(dirpath, f)
            for dirpath, dirnames, files in os.walk(source_dir)
            for f in fnmatch.filter(files, '*.jpg')]
    images = [] # Empty image list
    for file in image_files: # Example file: images_exp2\living\Mammals\Canidae\can_1.jpg
            fsplit = file.split(os.sep) # Example: ["images_exp2", "living", "Mammals", "Canidae", "can_1.jpg"]
            categories = [
                fsplit[-2], # Example: "Canidae"
                fsplit[-3], # Example: "Mammals"
            ]
            name = os.path.splitext(fsplit[-1])[0] # Cut off ".jpg" from file name
            image_stim = visual.ImageStim(window, file, size=3, name='{}.{}'.format(categories[0], name)) # Load the image stimulus (example name: "Canidae.can_1"
            images.append(Image(name, categories, image_stim)) # Fills image list
    return images

if __name__ == '__main__': # If this file was run directly
    window = visual.Window([1360, 768], monitor='samsung', units='deg',
                           fullscr=True, allowGUI=False,
                           color=1, screen=0)
    subject = create_subject(
        important_categories=[
            ImportantCategory('Dog', 'Cat', '?'),
            ImportantCategory('Cat', 'Dog', '?'),
        ])
    images = load_images(
        window=window,
        source_dir=os.path.join(os.getcwd(), 'images_exp2')
    )
    tracker = pylinkwrapper.connect(window, subject.id)
    tracker.tracker.setPupilSizeDiameter('YES')
    tracker.calibrate()
    exp = Experiment(
        subject=subject,
        questions=[
            ('How hungry are you?', '1 = Not hungry ... 7 = Very hungry'),
            ('How tired are you?', '1 = Not tired ... 7 = Very tired'),
        ],
        blocks=[
            Block(8, 4, 48),
            Block(8, 4, 48),
            Block(8, 4, 48),
            Block(8, 4, 48),
            Block(8, 4, 48),
        ],
        images=images,
    )
    exp.run(window, tracker, output_file)