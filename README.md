# ttrpg-dm-board

## A control board for Dungeon Masters to use in table top role playing games like DND.

Written with python and the pygame library, with the help of Claude 3.5.

### Current features

#### Soundboard

        Ambient tracks
        - ambient tracks can be faded in and out, paused/resumed, and queued
        - when an ambient track finishes, the next track from the queue will be played: if the queue
        is empty, the track will loop
        - multiple tracks can be mapped to one button, one of which will be randomly chosen when the button is clicked
        Sound effects
        - sound effects will play a single sound omce
        - they can be played on top of ambient tracks
        - multiple effects can be mapped to one button, one of which will be randomly chosen when the button is clicked
    
    - all sounds are normalized when the program starts
    - separate volume sliders for ambient tracks and sound effects
