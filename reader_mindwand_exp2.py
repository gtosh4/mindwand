import csv
import fnmatch
import os
from random import choice, shuffle

import numpy as np
from psychopy import core, gui, visual, event

import pylinkwrapper


class Image:
    def __init__(self, name, categories, image_stim):
        # Name is the image's file name (eg 'dog_1' from 'dog_1.jpg')
        self.name = name

        # Categories in descending specificity (eg ['Dog', 'Mammal', 'Living'])
        self.categories = categories

        self.image_stim = image_stim


class Subject:
    def __init__(self, id, target):
        self.id = id
        self.target = target


# TUT Probe
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
        # Initiate TUTprop clock
        self.time = core.Clock()
        self.next_probe = np.random.randint(15, 31)

    def try_probe(self, is_last_trial):
        probetime = self.time.getTime()
        # Only test TUT every 15-31 seconds (randomly) or on the last trial
        if probetime >= self.next_probe or is_last_trial:
            # Prope TUT severity & reset
            tutrating = self.probe()
            self.time.reset()
            self.next_probe = np.random.randint(15, 31)

            # Save Results
            return (
                tutrating,
                round(probetime, 2)
            )
        else:
            return (0, 0)

    # Function for display
    def probe(self):
        # Display and collect response
        while self.ratingScale.noResponse:
            self.rtxtob.draw()
            self.ratingScale.draw()
            self.win.flip()

        # Return and Reset
        rating = self.ratingScale.getRating()
        self.ratingScale.reset()
        return rating


class Trial:
    def __init__(self, trial_num, images, trial_type):
        self.trial_num = trial_num
        self.images = images
        self.trial_type = trial_type

    def setup_tracker(self, window, tracker, fix):
        # Check for fixation
        tracker.fixCheck(2, 0.1, 'z')

        # Pupil time
        tracker.setStatus('Pupil Time')
        tracker.setTrialID()
        tracker.drawIA(0, 0, 2, 1, 1, 'pfixation')
        tracker.sendMessage('pupiltime')
        fix.draw()
        tracker.recordON()
        window.flip()
        core.wait(1)
        tracker.recordOFF()
        tracker.setTrialResult()

    def setup_images(self, tracker):
        # Randomize coordinates
        coords = [(x, y) for y in [-4, 0, 4] for x in np.linspace(-10, 10, 4)]
        del coords[5:7]  # Delete the middle section
        coords = [xy + np.random.uniform(-0.5, 0.5, 2) for xy in coords]

        # Draw IAs
        tracker.drawIA(0, 0, 2, 1, 1, 'fixation')
        for index, xy in enumerate(coords):
            image = self.images[index]

            image.image_stim.setPos(xy)

            tracker.drawIA(xy[0], xy[1], 3, index + 2, index + 2, image.image_stim.name)

    def draw_loop(self, window, dots):
        keyps = []
        start_time = None
        while not keyps:
            # Images
            for image in self.images:
                image.image_stim.draw()

            # Dots
            dots.draw()

            # Display
            flip_time = window.flip()
            if not start_time:
                start_time = flip_time

            # Check for key press
            keyps = event.getKeys(keyList=['space', 'return', 'escape'],
                                  timeStamped=True)

        return (
            keyps[0][0],  # Key pressed
            start_time - keyps[0][1],  # Response time
        )


class Experiment:
    def __init__(self, subject, questions, trials):
        self.subject = subject
        self.questions = questions
        self.trials = trials
        
    def instruct(self, window, tcat):
        # Show instructions
        itxt = ('You are looking for {}!\n\n'
                'If one is present - press ENTER\n\n'
                'If one is NOT present - press the SPACEBAR'.format(tcat))
        
        itxt = itxt.replace('_', ' ')
        
        visual.TextStim(window, itxt, color = -1, wrapWidth = 25).draw()
        window.flip()
        event.waitKeys()

    def ask_questions(self, window):
        question_responses = []
        for question, scale in self.questions:
            question_text = visual.TextStim(window, text=question, color=-1)  # Question text
            scale_rating = visual.RatingScale(window, scale=scale, textColor=-1,
                                              lineColor=-1, noMouse=True)  # Scale rating
            # Update until response
            while scale_rating.noResponse:
                question_text.draw()
                scale_rating.draw()
                window.flip()

            question_responses.append(scale_rating.getRating())
            scale_rating.reset()
        return question_responses

    def run(self, window, tracker, output_file, experiment_path):
        subject_id = self.subject.id
        target_category = self.subject.target
        question_responses = self.ask_questions(window)
        self.instruct(window, target_category)
        
        # Stimuli
        fix = visual.Circle(window, radius=0.125, pos=(0, 0), fillColor=-1,
                            lineColor=-1)
        # Make Noise nots
        dots = visual.DotStim(window, coherence=0, fieldSize=(25, 15), color=-1,
                              nDots=10000)

        # Start clock
        exptime = core.Clock()

        # TUT
        tut = TUTProbe(window)

        # Write the header to the output file
        header = [
            'sub',      # Subject id
            'tcateg',   # Target category
            'tnum',     # Trial number
            'tar',      # If target was present
            'sim',      # If similar was present
            'resp',     # The response key
            'rtype',    # The response type (one in ['hi', 'mi', 'fa', 'cr'])
            'rt',       # Response time
            'time',     # Trial start time
            'tutra',    # TUT rating
            'tuttime',  # TUT test time
            'hunger',   # The first question's response
            'tired',    # The second question's response
        ]
        output_file.writerow(header)

        total_trials = len(self.trials)
        current_trial_num = 0
        for trial_num, trial in enumerate(self.trials): # Go through trials
            current_trial_num += 1

            trial.setup_tracker(window, tracker, fix)

            # Eye-tracker pre-stim
            statmsg = 'Experiment {}%% complete. Current Trial: {}'.format(
                round(current_trial_num / total_trials, 3) * 100,
                current_trial_num)
            tracker.setStatus(statmsg)
            tracker.setTrialID()

            trial.setup_images(tracker)

            # Start recording
            tracker.recordON()

            # Reset for upcoming stimulus display
            event.clearEvents()
            trial_time = round(exptime.getTime(), 2)

            # Draw images and await a response
            key, response_time = trial.draw_loop(window, dots)

            # Quit?
            if key == 'escape':
                tracker.endExperiment(experiment_path)
                core.quit()

            # Parse Response
            if trial.trial_type == 'target':
                response_type = (
                    'hi' if key == 'return'
                    else 'mi' if key == 'space'
                    else None)
            else:
                response_type = (
                    'fa' if key == 'return'
                    else 'cr' if key == 'space'
                    else None)

            # Run TUT if it's time, or use the previous results
            tutra, tuttime = tut.try_probe(current_trial_num == total_trials)

            # See "Write the header..." for descriptions
            trial_results = dict(
                sub=subject_id,
                tcateg=target_category,
                tnum=current_trial_num,
                tar=(trial.trial_type == 'target' or trial.trial_type == 'similar'),
                sim=(trial.trial_type == 'similar'),
                resp=key,
                rtype=response_type,
                rt=response_time,
                time=trial_time,
                tutra=tutra,
                tuttime=tuttime,
                hunger=question_responses[0],
                tired=question_responses[1],
            )

            # Eye-tracker post-stim
            for key, value in trial_results.iteritems():
                tracker.sendVar(key, value)
            tracker.setTrialResult()

            # Write trial info
            output_file.writerow([trial_results[col] for col in header])

            # ISI
            fix.draw()
            window.flip()
            core.wait(2)

        tracker.endExperiment(experiment_path)
        core.quit()


def create_subject(targets):
    expinfo = {
        'Subject ID': '',
        'Target Category': targets  # Show options as target names
    }
    # Shows dialog box and quits experiment when cancel is clicked
    if not gui.DlgFromDict(expinfo, title='Subject Info').OK:
        core.quit()

    # Get the results from the dialog box
    id = expinfo['Subject ID']
    target = expinfo['Target Category']

    return Subject(id, target)


def load_trials(window, image_dir, trials_dir, target):
    visual.TextStim(window, 'Loading Trials...', color=-1).draw()  # Window that says Loading Images
    window.flip()
    
    trials_file = csv.reader(open(os.path.join(trials_dir, target + '_recorder.csv'), 'rb'))
    trial_specification = {}
    for row_num, row in enumerate(trials_file):
        if row_num == 0:
            # Skip the header row
            continue
        tnum = int(row[0])
        name = row[1]
        position = row[2]
        trial_type = row[3]
        if tnum not in trial_specification:
            trial_specification[tnum] = []
        trial_specification[tnum].append((name, position, trial_type))

    # Find all the images files within source_dir
    image_files = [
        os.path.join(dirpath, f)
        for dirpath, dirnames, files in os.walk(image_dir)
        for f in fnmatch.filter(files, '*.jpg')]
    images = {}  # Empty image list
    for image_file in image_files:  # Example file: images_exp2\living\Mammals\Canidae\can_1.jpg
        fsplit = image_file.split(os.sep)  # Example: ["images_exp2", "living", "Mammals", "Canidae", "can_1.jpg"]
        categories = [
            fsplit[-2],  # Example: "Canidae"
            fsplit[-3],  # Example: "Mammals"
        ]
        name = os.path.splitext(fsplit[-1])[0]  # Cut off ".jpg" from file name
        # Load the image stimulus (example name: "Canidae.can_1")
        image_stim = visual.ImageStim(window, image_file, size=3, name='{}.{}'.format(categories[0], name))

        images[name] = Image(name, categories, image_stim)  # Fills image list
        
    trials = []
    for tnum, trial_image_specification in trial_specification.iteritems():
        # Sort the images by position
        trial_image_specification = sorted(trial_image_specification, key=lambda spec: spec[1])
        
        trial_images = []
        for specification in trial_image_specification:
            spec_image_name = specification[0]
            if spec_image_name not in images:
                raise AssertionError('No image by name {} found. Found images: {}'.format(spec_image_name, ','.join(images.keys())))
            else:
                trial_images.append(images[spec_image_name])
        trial_type = trial_image_specification[0][2] # All specs should have the same type for the same trial
        trials.append(Trial(trial_num=tnum, images=trial_images, trial_type=trial_type))

    # Sort the trials by the trial num so it runs them in the correct order
    trials = sorted(trials, key=lambda trial: trial.trial_num)
    return trials


def main():
    subject = create_subject(
        targets=[
            'Cats',
        ])
    # Create the window after creating the subject so that the window doesn't block the view of the
    # subject dialog box
    window = visual.Window([2560, 1440], monitor='PhilMon', units='deg',
                           fullscr=True, allowGUI=False,
                           color=1, screen=0)
    trials=load_trials(
        window=window,
        image_dir=os.path.join(os.getcwd(), 'images_exp2'),
        trials_dir=os.path.join(os.getcwd(), 'trials_exp2'),
        target=subject.target
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
        trials=trials,
    )
    output_file = csv.writer(open(os.path.join(os.getcwd(), 'data_exp2', subject.id + '_mindwand_exp2.csv'), 'wb'))
    experiment_path = 'C:\\Dropbox\\Exps_Nick\\mindwand\\edfs_exp2\\'

    exp.run(window, tracker, output_file, experiment_path)


if __name__ == '__main__':  # If this file was run directly
    main()
