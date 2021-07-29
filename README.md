# Team Baygulls
## BWSI Autonomous Underwater Vehicle Challenge
- [v0.6.0]: Same as [v0.4.0] but fixed bug.
- [v0.5.0]: Calculates rudder position by doing delta_angle * 2. Fix bugs and improved image processor
- [v0.4.0]: Calculates rudder position by doing delta_angle ** 1.25 / 1.5. Fix bugs and improved image processor
- [v0.3.0]: Same as [v0.1.0] but fixed bugs after testing on AUV.
- [v0.2.0]: calculated rudder position by doing delta_angle ** 1.25 / 1.5 in __select_command method in AUV_Controller.py. Simulated AUV passed through 3 out of 5 gates consistently.
- [v0.1.0]: calculated rudder position by multiplying delta_angle by **2** in __select_command method in AUV_Controller.py. Simulated AUV passed through 2-5 out of 5 gates when rudder position was multiplied by **3**, but Joe, our instructor, said it was a bit aggressive when he ran the code on the AUV.

- ChallengeCodePi: Run on the AUV's Raspberry Pi. Upgrade numpy and opencv-python to the latest version.
- ChallengeCode: Run on computer for developing (simulator)

vehicle_sim and vehicle_code are older versions of the simulator.
