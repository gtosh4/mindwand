# Mind wandering task
# N. DiQuattro - Winter 2015
# updated jessica 12/2015 for exp 2

# Import modules
from psychopy import visual
from psychopy import core, event, gui
import numpy as np
import csv, fnmatch, os
from random import choice, shuffle, sample

# Eye tracking imports
import pylinkwrapper

# Window set-up
win = visual.Window([1920, 1200], monitor='Asus', units='deg',
                    fullscr=True, allowGUI=False,
                    color=1, screen=0)
# Stimuli
fix = visual.Circle(win, radius=0.125, pos=(0, 0), fillColor=-1,
                    lineColor=-1)
# Make Noise nots
dots = visual.DotStim(win, coherence=0, fieldSize=(25, 15), color=-1,
                      nDots=10000)


# Defining experiment contents
class Experiment:
    """
    An experiment is set up with a set of target categories.
    Calling setup() will create a dialog box asking the subject ID and which target (from target_cats) to use.
    """

    def __init__(self, target_cats, questions):
        self.target_cats = target_cats
        self.questions = questions
        self.question_responses = []
        self.subj_id = ''
        self.target = ''
        self.log = None
        self.tracker = None
        self.image_files = []
        self.images_by_cat = {}

    # Running this will pop up a dialog asking what the subject ID and what the target category is
    def setup_subject(self):
        expinfo = {'Subject ID': '', 'Target Category': self.target_cats}
        if not gui.DlgFromDict(expinfo, title='Subject Info').OK:
            core.quit()
        self.subj_id = expinfo['Subject ID']
        self.target = expinfo['Target Category']

    # Running this will set up the log file (the csv)
    def setup_log(self):
        log_fname = self.subj_id + '_mindwand_exp2.csv'
        log_file = open(os.path.join('data_exp2', log_fname), 'wb')
        self.log = csv.writer(log_file)

    # Running this will set up and calibrate the tracker
    def setup_tracker(self):
        self.tracker = pylinkwrapper.connect(win, self.subj_id)
        self.tracker.tracker.setPupilSizeDiameter('YES')
        self.tracker.calibrate()

    # Running this will find all the image files (but not load them)
    def setup_image_files(self):
        self.image_files = [
            os.path.join(dirpath, f)
            for dirpath, dirnames, files in os.walk(os.path.join(os.getcwd(), 'images_exp2'))
            for f in fnmatch.filter(files, '*.jpg')]

    # Running this (after setup_image_files) will load the found images
    def load_images(self):
        def make_image(fpath, cat2, name):
            name1 = '{}.{}'.format(cat2, name)
            img = visual.ImageStim(win, fpath, size=3, name=name1)
            return img

        for ifn in self.image_files:
            fsplit = ifn.split(os.sep)
            fpath = ifn
            # Example fpath: images_exp2\living\Mammals\Canidae\can_1.jpg
            cat1 = fsplit[-3] # Example Mammals
            cat2 = fsplit[-2] # Example Canidae
            name = os.path.splitext(fsplit[-1])[0]
            if (cat1, cat2) not in self.images_by_cat:
                self.images_by_cat[(cat1, cat2)] = []
            self.images_by_cat[(cat1, cat2)].append(make_image(fpath, cat2, name))

    def get_target_images(self):
        target_images = []
        for (cat1, cat2), images in self.images_by_cat:
            if cat2 == self.target:
                target_images += images
        return target_images

    def get_distrators_by_cat1(self):
        distractors_by_cat1 = {}
        for (cat1, cat2), images in self.images_by_cat:
            if cat2 != self.target:
                if cat1 not in distractors_by_cat1:
                    distractors_by_cat1[cat1] = []
                distractors_by_cat1[cat1] += images
        return distractors_by_cat1

    # Running this will show the instructions in a text box
    def show_instructions(self):
        itxt = ('You are looking for {}!\n\n'
                'If one is present - press ENTER\n\n'
                'If one is NOT present - press the SPACEBAR'.format(self.target))

        itxt = itxt.replace('_', ' ')

        visual.TextStim(win, itxt, color=-1, wrapWidth=25).draw()
        win.flip()
        event.waitKeys()

    # Running this will ask the questions and return the responses (in the same order as the questions)
    def ask_questions(self):
        self.question_responses = []
        for question, scale in self.questions:
            tob = visual.TextStim(win, text=question, color=-1)
            sca = visual.RatingScale(win, scale=scale, textColor=-1,
                                     lineColor=-1, noMouse=True)
            # Update until response
            while sca.noResponse:
                tob.draw()
                sca.draw()
                win.flip()

            self.question_responses.append(sca.getRating())
            sca.reset()

    ## Experiment Structure
    def initialize_trials(self, bnum):
        # make trials
        trial_list = []
        for reps in range(100):
            # Target trial?
            if reps < 81:
                tarpres = False
            else:
                tarpres = True

            trial_list.append({
                            'sub'     : self.subj_id,
                            'tcat'    : self.target,
                            'tar'     : tarpres,
                            'resp'    : 'NA',
                            'rtype'   : 'NA',
                            'rt'      : 'NA',
                            'time'    : 'NA',
                            'tutra'   : 'NA',
                            'tuttime' : 'NA',
                            'hunger'  : self.question_responses[0],
                            'tired'   : self.question_responses[1]
                        })

        # Randomize trials
        shuffle(trial_list)

        # Add trial/block number
        for i, trial in enumerate(trial_list):
            trial['tnum'] = i + 1 + (len(trial_list) * bnum)
            trial['bnum'] = bnum + 1

        return trial_list

    ## Block Runner
    def run_block(self, bnum, hwrite = False, prac = False, last = False):
        tut = TUTProbe()
        # Initiate TUTprop clock
        tuttime = core.Clock()
        tutgo = np.random.randint(15, 31)

        # Make Trial list and iterate
        trial_list = self.initialize_trials(bnum)
        for trial in trial_list:
            # Randomize coordinates
            coords = [(x, y) for y in [-4, 0, 4] for x in np.linspace(-10, 10, 4)]
            del coords[5:7]
            coords = [xy + np.random.uniform(-.5, .5, 2) for xy in coords]

            # Grab stimuli
            target_images = self.get_target_images()
            target_stim_index = np.random.randint(len(target_images)) # choose random target
            target_stim_image = target_images[target_stim_index]

            category_distractors = []
            for cat1, images in self.get_distrators_by_cat1():
                category_distractors.append(choice(images))

            all_distractor_images = []
            for cat1, images in self.get_distrators_by_cat1():
                all_distractor_images += images

            random_distractors_by_name = {}
            # choose 4 random distractors to make a final 10 distractor images
            while len(random_distractors_by_name) != 4:
                distractor = choice(all_distractor_images)
                random_distractors_by_name[distractor.name] = distractor

            chosen_distractor_images = category_distractors + random_distractors_by_name.values()

            # Pick random target position
            tloc = np.random.randint(10)

            # Set coordinates for images
            for xyi, xy in enumerate(coords):
                if trial['tar'] and xyi == tloc:
                    target_stim_image.setPos(xy)
                else:
                    chosen_distractor_images[xyi].setPos(xy)

            # Check for fixation
            self.tracker.fixCheck(2, .1, 'z')

            # Pupil time
            self.tracker.setStatus('Pupil Time')
            self.tracker.setTrialID()
            self.tracker.drawIA(0, 0, 2, 1, 1, 'pfixation')
            self.tracker.sendMessage('pupiltime')
            fix.draw()
            self.tracker.recordON()
            win.flip()
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
                if trial['tar'] and csi == tloc:
                    name = 'target.%s' % target_stim_image.name
                else:
                    name = 'nonTarget.%s' % chosen_distractor_images[csi].name

                self.tracker.drawIA(cs[0], cs[1], 3, csi+2, csi+2, name)

            # Start recording
            self.tracker.recordON()

            # Reset for upcoming stimulus display
            lcount = 0
            event.clearEvents()
            keyps = []
            trial['time'] = round(exptime.getTime(), 2)

            # Draw loop
            while not keyps:
                # Images
                for xyi, xy in enumerate(coords):
                    if trial['tar'] and xyi == tloc:
                        target_stim_image.draw()
                    else:
                        chosen_distractor_images[xyi].draw()

                # Dots
                dots.draw()

                # Display
                if lcount == 0:
                    lcount += 1
                    stim_on = win.flip()

                    # Screenshot
                    #fileName = 'jessicascreen'
                    #win.getMovieFrame()
                    #fileName=str(fileName)+'.png'
                    #win.saveMovieFrames(fileName)
                    #win.movieFrames=[]
                else:
                    win.flip()

                # Check for key press
                keyps = event.getKeys(keyList=['space', 'return', 'escape'],
                                      timeStamped=True)

            # Stop Recording
            self.tracker.recordOFF()

            # Save Response info
            trial['resp'] = keyps[0][0]
            trial['rt'] = round((keyps[0][1] - stim_on) * 1000, 2)

            # Parse Response
            if trial['tar'] and keyps[0][0] == 'return':
                trial['rtype'] = 'hi'
            elif trial['tar'] and keyps[0][0] == 'space':
                trial['rtype'] = 'mi'
            elif not trial['tar'] and keyps[0][0] == 'return':
                trial['rtype'] = 'fa'
            elif not trial['tar'] and keyps[0][0] == 'space':
                trial['rtype'] = 'cr'

            # Quit?
            if keyps[0][0] == 'escape':
                self.tracker.endExperiment('C:\\edfs\\Nick\\mindwand\\')
                core.quit()

            # TUT time
            probetime = tuttime.getTime()
            if probetime >= tutgo or trial['tnum'] == 300:
                # Prope TUT severity & reset
                tutrate = tut.tutprobe()
                tuttime.reset()
                tutgo = np.random.randint(15, 31)

                # Save Results, apply to preceding trials
                trial['tutra'] = tutrate
                trial['tuttime'] = round(probetime, 2)

            # Eye-tracker post-stim
            for key, value in trial.iteritems():
                self.tracker.sendVar(key, value)
            self.tracker.setTrialResult()

            # Write header
            if hwrite:
                self.log.writerow(trial.keys())
                hwrite = False

            # Write trial info
            self.log.writerow(trial.values())

            # ISI
            fix.draw()
            win.flip()
            core.wait(2)

    def end(self):
        # Eye-tracker clean-up
        self.tracker.endExperiment('C:\\edfs\\Nick\\mindwand\\')
        core.quit()


## TUT Probe
class TUTProbe:
    def __init__(self):
        # Make scale
        rtxt = ('On the scale below, rate the duration of task unrelated thoughts '
                'since the last probe')
        self.rtxtob = visual.TextStim(win, text=rtxt, pos=(0, 3), height=1,
                                      color=-1)

        # Define rating scale
        sctxt = '0 = Not at all ... 5 = The whole time'
        self.ratingScale = visual.RatingScale(win, low=0, high=5, scale=sctxt,
                                              labels=map(str, range(6)),
                                              tickMarks=range(6), textColor=-1,
                                              lineColor=-1, noMouse=True)

    # Function for display
    def tutprobe(self):
        # Display and collect response
        while self.ratingScale.noResponse:
            self.rtxtob.draw()
            self.ratingScale.draw()
            win.flip()

        # Return and Reset
        rating = self.ratingScale.getRating()
        self.ratingScale.reset()
        return rating

## Setup and Execute Experiment
if __name__ == '__main__':
    # Experiment Setup
    exp = Experiment(
        target_cats=['Canidae', 'Felidae'],
        questions=[
            ('How hungry are you?', '1 = Not hungry ... 7 = Very hungry'),
            ('How tired are you?', '1 = Not tired ... 7 = Very tired')
        ]
    )
    exp.setup_subject()
    exp.setup_log()
    exp.setup_tracker()
    exp.setup_image_files()

    # Make master list of images
    visual.TextStim(win, 'Loading Images...', color=-1).draw()
    win.flip()
    exp.load_images()

    exp.show_instructions()

    # Ask questions
    exp.ask_questions()

    # Instructions
    exp.show_instructions()

    # Start clock
    exptime = core.Clock()

    # Run Experiment blocks
    exp.run_block(0, hwrite=True)
    for bl in range(1, 3):
        exp.run_block(bl)

    exp.end()
