import time


from biohit_pipettor import Pipettor

p = Pipettor(1000, initialze=False)




p.y_speed = 6
p.x_speed = 6
p.z_speed = 3


p.move_xy(106.5, 83.5) # to where tips are
p.pick_tip(60)
p.move_z(5)
# use exclusively move_y bc frame on pipette tip box
    # p.eject_tip()
    p.move_y(175) # to stock solution well (currently at 97, 175)
    p.move_to_surface(70, 2) # dip tip in liquid
    p.aspirate() # pick up error margin vol to make sure all wells get exact amount of liquid
    p.move_z(10) # move up
    p.move_xy(142, 176.8) # to well position
    p.move_z(65) # to hit edge of well exactly
    p.move_z(30)

    for i in range(5):
       current_pos = p.xy_position
       offset = (18, 0)
       new_position = [x +y for x, y in zip(current_pos, offset)]
       p.move_xy(new_position[0], new_position[1])
       p.move_z(65)
       # dispense volume
       p.move_z(30)
   p.move_y() # tip discard location (fixed)

# more likely need to go to well, dispense, return to stock solution, move to offset position, dispense again

import time
time.sleep(in seconds)
    p.move_xy()
    current_pos = list(p.xy_position)
    print(current_pos)
    offset = [18.9, 0]
    new_position = [x +y for x, y in zip(current_pos, offset)]
    new_position = tuple(new_position)
    print(new_position)
    p.move_xy(new_position[0], new_position[1])
    
    # p.pick_tip(120) #pipette box potentially too low, pipette arm doesn´t lowr enough to pick anything up
    p.move_xy() # to stock solution well
    p.move_to_surface() # dip tip in liquid
    p.aspirate() # pick up error margin vol to make sure all wells get exact amount of liquid
    p.move_z() # move up
    p.move_xy() # to well position
    current_pos = p.xy_position
    p.move_to_surface()
    p.dispense()
    p.move_z() #up
    offset = []# xoffset, yoffset]
    new_position = current_pos + offset
    p.move_xy(new_position) # if this works with an object
    # go through wells per row only changing move x value and dispense in each, then return to aspirate more stock
    p.move_to_surface()
    p.dispense()
    p.move_z() # up
    p.move_xy() # tip discard location (fixed)
    p.eject_tip()
    p.x_speed = 5

