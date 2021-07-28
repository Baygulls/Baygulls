# Team Baygulls
- v.0.1: calculated rudder position by doing delta_angle ** 1.25 / 1.5 in __select_command method in AUV_Controller.py. Simulated AUV passed through 3 out of 5 gates consistently.
- v.0.0: calculated rudder position by multiplying delta_angle by **2** in __select_command method in AUV_Controller.py. Simulated AUV passed through 2-5 out of 5 gates when rudder position was multiplied by **3**, but Joe, our instructor, said it was a bit aggressive when he ran the code on the AUV.

- ChallengeCodePi: Run on the AUV's Raspberry Pi
- ChallengeCode: Run on computer for developing (simulator)

vehicle_sim and vehicle_code are older versions of the simulator.