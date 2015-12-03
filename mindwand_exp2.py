# Mind wandering task
# N. DiQuattro - Winter 2015
# updated jessica 12/2015 for exp 2

# Import modules
from psychopy import visual
from psychopy import core, event, gui, sound
import numpy as np
import csv, fnmatch, os
from random import sample

# Eye tracking imports
import pylinkwrapper

## Experiment Set-up
tcats = ['Aircraft', 'Amphibians', 'Arachnids',
         'Flowers', 'Gardening_Tools', 'Office_Tools']
expinfo = {'Subject ID' : '', 'Target Category' : tcats }

if not gui.DlgFromDict(expinfo, title = 'Subject Info').OK:
    core.quit()
    
# Window set-up
win = visual.Window([1920, 1200], monitor = 'Asus', units = 'deg',
                    fullscr = True, allowGUI = False,
                    color = 1, screen=0)

# Open logfile
fname = expinfo['Subject ID'] + '_mindwand_exp2.csv'
file = open(os.path.join('data_exp2', fname), 'wb')
log = csv.writer(file)

# Eye-tracker setup
tracker = pylinkwrapper.connect(win, expinfo['Subject ID'])
tracker.tracker.setPupilSizeDiameter('YES')
tracker.calibrate()

## Stimuli
fix = visual.Circle(win, radius = .125, pos = (0, 0), fillColor = -1,
                    lineColor = -1)
                    
# Get image filenames
imgfiles = [os.path.join(dirpath, f)
    for dirpath, dirnames, files in os.walk(os.path.join(os.getcwd(), 'images_exp2'))
    for f in fnmatch.filter(files, '*.jpg')]
    
# Make master list of images
visual.TextStim(win, 'Loading Images...', color = -1).draw()
win.flip()

imglist = []
for ifn in imgfiles:
    fsplit = ifn.split(os.sep)
    imglist += [{
                'fpath' : ifn,
                'cat1'  : fsplit[-3],
                'cat2'  : fsplit[-2],
                'name'  : os.path.splitext(fsplit[-1])[0]
                }]

# Target & distractor lists
def ImageMaker(fpath, cat, name):
    name1 = '{}.{}'.format(cat, name)
    img = visual.ImageStim(win, fpath, size = 3, name = name1)
    return(img)
    
tcat = expinfo['Target Category']
tarims = [ImageMaker(item['fpath'], item['cat2'], item['name'])
          for item in imglist if item["cat2"] == tcat]
          
disims = [ImageMaker(item['fpath'], item['cat2'], item['name'])
          for item in imglist if item["cat2"] != tcat]

# Make Noise nots
dots = visual.DotStim(win, coherence = 0, fieldSize = (25, 15), color = -1,
                        nDots = 10000)
                        
## Instructions
def instruct(tcat):
    # Show instructions
    itxt = ('You are looking for {}!\n\n'
            'If one is present - press ENTER\n\n'
            'If one is NOT present - press the SPACEBAR'.format(tcat))
            
    itxt = itxt.replace('_', ' ')
              
    visual.TextStim(win, itxt, color = -1, wrapWidth = 25).draw()
    win.flip()
    event.waitKeys()
    
## Ask questions
def askq():
    # set-up question variables
    qtxt = ['How hungry are you?', 'How tired are you?']
    scl  = ['1 = Not hungry ... 7 = Very hungry',
            '1 = Not tired ... 7 = Very tired']
    
    # Display each scale
    resps = []
    for qs in range(2):
        tob = visual.TextStim(win, text = qtxt[qs], color = -1)
        sca = visual.RatingScale(win, scale = scl[qs], textColor = -1,
                                 lineColor = -1, noMouse = True)
        # Update until response
        while sca.noResponse:
            tob.draw()
            sca.draw()
            win.flip()
            
        resps.append(sca.getRating())
        sca.reset()
        
    return(resps)

## TUT Probe
# Make scale
rtxt = ('On the scale below, rate the duration of task unrelated thoughts '
        'since the last probe')
rtxtob = visual.TextStim(win, text = rtxt, pos = (0, 3), height = 1,
                         color = -1)

# Define rating scale
sctxt = '0 = Not at all ... 5 = The whole time'
ratingScale = visual.RatingScale(win, low = 0, high = 5, scale = sctxt,                        
                                    labels = map(str, range(6)),
                                    tickMarks = range(6), textColor = -1,
                                    lineColor = -1, noMouse = True)
                                    
# Function for display                                    
def tutprobe():    
    # Display and collect response
    while ratingScale.noResponse:
        rtxtob.draw()
        ratingScale.draw()
        win.flip()
        
    # Return and Reset
    rating = ratingScale.getRating()
    ratingScale.reset()
    return(rating)

## Experiment Structure
def makeTrialList(bnum, prac = False):
    # make trials
    trialList = []
    for reps in range(100):
        # Target trial?
        if reps < 81:
            tarpres = False
        else:
            tarpres = True
            
        trialList += [{
                        'sub'     : expinfo['Subject ID'],
                        'tcat'    : expinfo['Target Category'],
                        'tar'     : tarpres,
                        'resp'    : 'NA',
                        'rtype'   : 'NA',
                        'rt'      : 'NA',
                        'time'    : 'NA',
                        'tutra'   : 'NA',
                        'tuttime' : 'NA',
                        'hunger'  : quest[0],
                        'tired'   : quest[1]
                    }]
    
    # Randomize trials
    trialList = sample(trialList, len(trialList))
    
    # Add trial/block number
    for i, trial in enumerate(trialList):
        trial['tnum'] = i + 1 + (len(trialList) * bnum)
        trial['bnum'] = bnum + 1
        
    return(trialList)

## Block Runner
def runBlock(bnum, hwrite = False, prac = False, last = False):
    # Initiate TUTprop clock
    tuttime = core.Clock()
    tutgo = np.random.randint(15, 31)
        
    # Make Trial list and iterate
    trialList = makeTrialList(bnum, prac)
    for trial in trialList:
        # Randomize coordinates
        coords = [(x,y) for y in [-4, 0, 4] for x in np.linspace(-10, 10, 4)]
        del coords[5:7]        
        coords = [xy + np.random.uniform(-.5, .5, 2) for xy in coords]
        
        # Grab stimuli
        tstim = np.random.randint(len(tarims)) # choose random target
        trialds = sample(disims, 10)  # choose 10 distractors

        # Pick random target position
        tloc = np.random.randint(10)
        
        # Set coordinates for images
        for xyi, xy in enumerate(coords):
            if trial['tar'] and xyi == tloc:
                tarims[tstim].setPos(xy)
            else:
                trialds[xyi].setPos(xy)
                
        # Check for fixation
        tracker.fixCheck(2, .1, 'z')
                
        # Pupil time
        tracker.setStatus('Pupil Time')
        tracker.setTrialID()
        tracker.drawIA(0, 0, 2, 1, 1, 'pfixation')
        tracker.sendMessage('pupiltime')
        fix.draw()
        tracker.recordON()
        win.flip()
        core.wait(1)
        tracker.recordOFF()
        tracker.setTrialResult()
                
        # Eye-tracker pre-stim
        statmsg = 'Experiment {}%% complete. Current Trial: {}'.format(round(trial['tnum'] / 300.0, 3) * 100, trial['tnum'])
        tracker.setStatus(statmsg)
        tracker.setTrialID()
        
        # Draw IAs
        tracker.drawIA(0, 0, 2, 1, 1, 'fixation')
        for csi, cs in enumerate(coords):
            # set name
            if trial['tar'] and csi == tloc:
                name = 'target.%s' % tarims[tstim].name
            else:
                name = 'nonTarget.%s' % trialds[csi].name
                
            tracker.drawIA(cs[0], cs[1], 3, csi+2, csi+2, name)
                
        # Start recording
        tracker.recordON()
                
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
                    tarims[tstim].draw()
                else:
                    trialds[xyi].draw()

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
            keyps = event.getKeys(keyList = ['space', 'return', 'escape'],
                timeStamped = True)
        
        # Stop Recording
        tracker.recordOFF()
        
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
            tracker.endExperiment('C:\\edfs\\Nick\\mindwand\\')
            core.quit()
            
        # TUT time
        probetime = tuttime.getTime()
        if probetime >= tutgo or trial['tnum'] == 300:
            # Prope TUT severity & reset
            tutrate = tutprobe()
            tuttime.reset()
            tutgo = np.random.randint(15, 31)
            
            # Save Results, apply to preceding trials
            trial['tutra'] = tutrate
            trial['tuttime'] = round(probetime, 2)

        # Eye-tracker post-stim
        for key, value in trial.iteritems():
            tracker.sendVar(key, value)
        tracker.setTrialResult()
            
        # Write header
        if hwrite:
            log.writerow(trial.keys())
            hwrite = False
        
        # Write trial info
        log.writerow(trial.values())
        
        # ISI
        fix.draw()
        win.flip()
        core.wait(2)

## Execute Experiment

# Ask questions
quest = askq()

# Instructions
instruct(tcat)

# Start clock
exptime = core.Clock()

# Run blocks
runBlock(0, hwrite = True)
for bl in range(1, 3):
    runBlock(bl)

# Eye-tracker clean-up
tracker.endExperiment('C:\\edfs\\Nick\\mindwand\\')
core.quit()