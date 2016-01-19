import csv
import fnmatch
import os
from random import choice, shuffle


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
    def __init__(self, images, important_category, trial_type):
        self.images = images
        self.important_category = important_category
        self.trial_type = trial_type


class Block:
    def __init__(self, number_of_target_trials, number_of_similar_trials, number_of_random_trials):
        self.number_of_target_trials = number_of_target_trials
        self.number_of_similar_trials = number_of_similar_trials
        self.number_of_random_trials = number_of_random_trials
        self.total_trials = number_of_target_trials + number_of_similar_trials + number_of_random_trials

    def generate_trials(self, images, important_category):
        # Filters for target images at level 0
        all_target_images = filter(
            lambda image: image.categories[0] == important_category.target,
            images
        )

        # Crash the program if no target images are found
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

        # important for selecting by level1
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

        trials = []  # empty trial list

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
        for target_trial_num in range(self.number_of_target_trials):
            trial_images = [choice(all_target_images)]
            trial_images.extend([
                                    choice(level1_images)  # Choose a random images from the level1 images
                                    for level1_images in distractors_by_level1.values()
                                    # Go through all level1 categories
                                    ])
            while len(trial_images) < 10:
                distractor = choice(all_distractors)
                is_duplicate = False  # Default state is 'not a duplicate'
                for image in trial_images:
                    if image.categories[0] == distractor.categories[0]:
                        is_duplicate = True

                if not is_duplicate:  # Only add non-duplicates to the trial images
                    trial_images.append(distractor)

            shuffle(trial_images)
            trials.append(
                Trial(images=trial_images, important_category=important_category, trial_type='target'))
        return trials

    def generate_similar_trials(self, important_category, all_target_images, all_distractors, all_similar_images,
                                distractors_by_level1):
        trials = []
        for similar_trial_num in range(self.number_of_similar_trials):
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

            shuffle(trial_images)
            trials.append(
                Trial(images=trial_images, important_category=important_category, trial_type='similar'))
        return trials

    def generate_random_trials(self, important_category, all_distractors, distractors_by_level1):
        trials = []
        for random_trial_num in range(self.number_of_random_trials):
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

            shuffle(trial_images)
            trials.append(Trial(trial_images, important_category, 'random'))
        return trials 


def record(image_log_file, blocks, images, target):
  image_log_header = [
      'tnum',
      'name',
      'position',
      'trial_type',
  ]
  if image_log_file:
      image_log_file.writerow(image_log_header)
  
  total_trials = sum(block.total_trials for block in blocks)
  current_trial_num = 0
  for block_num, block in enumerate(blocks): # Go through all the blocks
      for trial_num, trial in enumerate(block.generate_trials(images, target)): # For the current block, generate the trials and go through them
          current_trial_num += 1

          if image_log_file:
              for position, image in enumerate(trial.images):
                  image_log_file.writerow([
                      current_trial_num,
                      image.name,
                      position,
                      trial.trial_type,
                  ]) 


def load_images(source_dir):
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

        images.append(Image(name, categories))  # Fills image list
    return images


def main():
    blocks=[
        Block(8, 4, 48),
        Block(8, 4, 48),
        Block(8, 4, 48),
        Block(8, 4, 48),
        Block(8, 4, 48),
    ]
    images = load_images(
        source_dir=os.path.join(os.getcwd(), 'images_exp2')
    )
    target = ImportantCategory('Cats', 'Dogs', 'Utility_Vehicles')


    image_log_file = csv.writer(open(os.path.join(os.getcwd(), 'trials_exp2', target.target + '_recorder.csv'), 'wb'))
    record(image_log_file, blocks, images, target) 

if __name__ == '__main__':  # If this file was run directly
    main()