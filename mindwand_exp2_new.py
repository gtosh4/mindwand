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
        self.total_trials = targets + similars + randoms

    def generate_trials(self, images, important_category):
        trials = []  # empty trial list

        # Filters for target images at level 0
        all_target_images = filter(
            lambda image: image.categories[0] == important_category.target,
            images
        )

        if not all_target_images:
            raise AssertionError('No images found for target: {}'.format(important_category.target))
        
        all_similar_images = filter(
            lambda image: image.categories[0] == important_category.similar,
            images
        )
        
        if not all_similar_images:
            raise AssertionError('No images found for similar: {}'.format(important_category.similar))

        def is_distractor(image):
            return (
                image.categories[0] != important_category.target and  # Exclude target images
                image.categories[0] != important_category.remove  # Exclude images from the 'remove' category
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
            if level1 not in distractors_by_level1:  # Don't overwrite if the level1 is already there
                distractors_by_level1[level1] = []  # Initialize level1 to empty list
            distractors_by_level1[level1].append(image)  # Add image to its level1 list

        # Generate and add the target trials
        trials.extend(self.generate_target_trials(important_category, all_target_images, all_distractors,
                                                  distractors_by_level1))

        # Generate and add the similar trials
        trials.extend(self.generate_similar_trials(important_category, all_target_images, all_distractors,
                                                   all_similar_images, distractors_by_level1))

        # Generate and add the random trials
        trials.extend(self.generate_random_trials(important_category, all_distractors, distractors_by_level1))

        shuffle(trials)
        return trials

    def generate_target_trials(self, important_category, all_target_images, all_distractors, distractors_by_level1):
        trials = []
        for target_trial_num in range(self.targets):  # Create 'self.targets' number of target trials
            trial_images = [choice(all_target_images)]
            trial_images.extend([
                                    choice(level1_images)  # Choose a random images from the level1 images
                                    for level1_images in distractors_by_level1.values()
                                    # Go through all level1 categories
                                    ])
            while len(trial_images) < 10:
                distractor = choice(all_distractors)
                is_duplicate = False  # Default to not a duplicate
                for image in trial_images:
                    if image.categories[0] == distractor.categories[0]:
                        is_duplicate = True

                if not is_duplicate:  # Only add non-duplicates to the trial images
                    trial_images.append(distractor)

            trials.append(Trial(trial_images, important_category, 'target'))
        return trials

    def generate_similar_trials(self, important_category, all_target_images, all_distractors, all_similar_images,
                                distractors_by_level1):
        trials = []
        for similar_trial_num in range(self.similars):  # Create 'self.similars' number of similar trials
            trial_images = [
                choice(all_target_images),
                choice(all_similar_images),
            ]

            for level1_images in distractors_by_level1.values():
                level1_image = choice(level1_images)
                while level1_image.categories[0] == important_category.similar:  # Check if similar category is chosen
                    level1_image = choice(level1_images)  # Pick a new random one from the same level1
                trial_images.append(level1_image)

            while len(trial_images) < 10:
                distractor = choice(all_distractors)
                is_duplicate = False
                for image in trial_images:
                    if image.categories[0] == distractor.categories[0]:
                        is_duplicate = True

                if not is_duplicate:
                    trial_images.append(distractor)

            trials.append(Trial(trial_images, important_category, 'similar'))
        return trials

    def generate_random_trials(self, important_category, all_distractors, distractors_by_level1):
        trials = []
        for random_trial_num in range(self.randoms):  # Create 'self.randoms' number of random trials
            trial_images = []
            trial_images.extend([
                                    choice(level1_images)  # Choose a random images from the level1 images
                                    for level1_images in distractors_by_level1.values()
                                    # Go through all level1 categories
                                    ])
            while len(trial_images) < 10:
                distractor = choice(all_distractors)
                is_duplicate = False
                for image in trial_images:
                    if image.categories[0] == distractor.categories[0]:
                        is_duplicate = True

                if not is_duplicate:
                    trial_images.append(distractor)

            trials.append(Trial(trial_images, important_category, 'random'))
        return trials


class Experiment:
    def __init__(self, subject, questions, blocks, images, auto_run):
        self.subject = subject
        self.questions = questions
        self.blocks = blocks
        self.images = images
        self.auto_run = auto_run

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

    def run(self, window, tracker, output_file, experiment_path, image_log_file):
        subject_id = self.subject.id
        target_category = self.subject.target.target
        question_responses = self.ask_questions(window)

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
            'bnum',     # Block number
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

        image_log_header = [
            'sub',
            'tnum',
            'name',
            'categories',
        ]
        if image_log_file:
            image_log_file.writerow(image_log_header)
        
        total_trials = sum(block.total_trials for block in self.blocks)
        current_trial_num = 1
        for block_num, block in enumerate(self.blocks):
            for trial_num, trial in enumerate(block.generate_trials(self.images, self.subject.target)):
                current_trial_num += 1

                if image_log_file:
                    for image in trial.images:
                        image_log_file.writerow([
                            subject_id,
                            current_trial_num,
                            image.name,
                            ':'.join(image.categories),
                        ])

                trial.setup_tracker(window, tracker, fix, self.auto_run)

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
                key, response_time = trial.draw_loop(window, dots, self.auto_run)

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
                    bnum=(block_num + 1),
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
                if not self.auto_run:
                    core.wait(2)

        tracker.endExperiment(experiment_path)
        core.quit()


class Subject:
    def __init__(self, id, target):
        self.id = id
        self.target = target


class Trial:
    def __init__(self, images, important_category, trial_type):
        self.images = images
        self.important_category = important_category
        self.trial_type = trial_type

    def setup_tracker(self, window, tracker, fix, auto_run):
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
        if not auto_run:
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

            # set name
            if image.categories[0] == self.important_category.target:
                name = 'target.' + image.image_stim.name
            elif image.categories[0] == self.important_category.similar:
                name = 'similar.' + image.image_stim.name
            else:
                name = 'nonTarget.' + image.image_stim.name

            tracker.drawIA(xy[0], xy[1], 3, index + 2, index + 2, name)

    def draw_loop(self, window, dots, auto_run):
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
            
            if auto_run and not keyps: # Have the computer give a response if auto_run is set
                return (
                    choice(['space', 'return']), # Return a random key
                    0, # Zero response time for computers
                )
            
        return (
            keyps[0][0],  # Key pressed
            start_time - keyps[0][1],  # Response time
        )


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


def create_subject(important_categories):
    # Make a dictionary of target to category
    target_options = dict([(category.target, category) for category in important_categories])
    expinfo = {
        'Subject ID': '',
        'Target Category': target_options.keys()  # Show options as target names
    }
    # Shows dialog box and quits experiment when cancel is clicked
    if not gui.DlgFromDict(expinfo, title='Subject Info').OK:
        core.quit()

    # Get the results from the dialog box
    id = expinfo['Subject ID']
    target_category_name = expinfo['Target Category']

    target = target_options[target_category_name]  # Lookup the ImportantCategory for the target name
    return Subject(id, target)


def load_images(window, source_dir):
    visual.TextStim(window, 'Loading Images...', color=-1).draw()  # Window that says Loading Images
    window.flip()

    # Find all the images files within source_dir
    image_files = [
        os.path.join(dirpath, f)
        for dirpath, dirnames, files in os.walk(source_dir)
        for f in fnmatch.filter(files, '*.jpg')]
    images = []  # Empty image list
    for image_file in image_files:  # Example file: images_exp2\living\Mammals\Canidae\can_1.jpg
        fsplit = image_file.split(os.sep)  # Example: ["images_exp2", "living", "Mammals", "Canidae", "can_1.jpg"]
        categories = [
            fsplit[-2],  # Example: "Canidae"
            fsplit[-3],  # Example: "Mammals"
        ]
        name = os.path.splitext(fsplit[-1])[0]  # Cut off ".jpg" from file name
        # Load the image stimulus (example name: "Canidae.can_1"
        image_stim = visual.ImageStim(window, image_file, size=3, name='{}.{}'.format(categories[0], name))

        images.append(Image(name, categories, image_stim))  # Fills image list
    return images


def main(auto_run):
    subject = create_subject(
        important_categories=[
            ImportantCategory('Dogs', 'Cats', 'Utility_Vehicle'),
            ImportantCategory('Cats', 'Dogs', 'Cars_Trucks'),
        ])
    # Create the window after creating the subject so that the window doesn't block the view of the
    # subject dialog box
    window = visual.Window([1360, 768], monitor='samsung', units='deg',
                           fullscr=True, allowGUI=False,
                           color=1, screen=0)
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
        auto_run=auto_run,
    )
    output_file = csv.writer(open(os.path.join(os.getcwd(), 'data_exp2', subject.id + '_mindwand_exp2.csv'), 'wb'))
    # To disable image logging, comment out the following line and uncomment the line after.
    image_log_file = csv.writer(open(os.path.join(os.getcwd(), 'data_exp2', subject.id + '_mindwand_exp2_images.csv'), 'wb'))
    # image_log_file = None
    experiment_path = 'C:\\edfs\\Nick\\mindwand\\'

    exp.run(window, tracker, output_file, experiment_path, image_log_file)


if __name__ == '__main__':  # If this file was run directly
    # Change auto_run to True to have the computer set keys randomly
    main(auto_run=False)
