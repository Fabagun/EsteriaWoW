-- Sirus placements retain its Human camera, authored light, position and sequence.
local SIRUS_LOGIN_PATH = [[custom\esteria_login\sirus\]]
local MIDNIGHT_LOGIN_PATH = [[custom\esteria_login\midnight\interface\glues\models\ui_mainmenu_midnight\]]
local ESTERIA_LOGIN_SCENES = {
{ id = "mi", label = "Retail Midnight", layers = {
    { model = MIDNIGHT_LOGIN_PATH .. [[ui_mainmenu_midnight_02.m2]] },
    { model = MIDNIGHT_LOGIN_PATH .. [[ui_mainmenu_midnight.m2]] },
} },
{ id = "si", label = "Sirus WoW", layers = {
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\ui_mainmenu_sirusdefault.m2]] },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\humanmalefarmer.m2]],
        data = {1, -1.574, -1.663, -12.7, 2.456, 0.35, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\goober\g_fishingbobber.m2]],
        data = {1, -1.861, -2.436, -19.4, 2.456, 0.22, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[creature\frogduck\frogduck.m2]],
        data = {1, 2.026, -1.997, -14.4, 2.63, 0.37, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[creature\frogduck\frogduck.m2]],
        data = {1, -5.432, -1.526, -14.4, 1.059, 0.46, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\kalimdor\azshara\seaplants\starfish01_02\starfish01_02.m2]],
        data = {1, -5.736, -2.506, -16.6, 2.282, 0.25, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\generic\passivedoodads\particleemitters\blacksmith_smoke.m2]],
        data = {1, -2.523, 0.882, -12.5, -1.383, 0.01, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\generic\passivedoodads\particleemitters\blacksmith_smoke.m2]],
        data = {1, -2.911, 1.025, -12.5, -1.383, 0.01, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\generic\passivedoodads\particleemitters\blacksmith_smoke.m2]],
        data = {1, -3.327, 1.11, -12.5, -1.383, 0.02, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\generic\passivedoodads\particleemitters\blacksmith_smoke.m2]],
        data = {1, -0.959, 1.528, -12.5, -1.383, 0.01, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\generic\passivedoodads\particleemitters\blacksmith_smoke.m2]],
        data = {1, 0.555, 1.692, -12.5, -0.859, 0.01, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, -2.613, 1.534, -23.8, -1.034, 0.07, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, -2.229, 1.507, -22, -1.035, 0.08, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, -1.999, 1.556, -23.7, 1.059, 0.09, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, -1.653, 1.539, -22.2, -1.035, 0.1, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, -1.38, 1.801, -23.8, -1.035, 0.11, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, -1.016, 1.863, -23.8, -0.86, 0.12, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 0.25, 1.956, -24.1, -1.035, 0.13, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 0.659, 2.021, -23.8, -0.86, 0.13, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 2.063, 2.226, -23.8, -0.86, 0.15, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 2.63, 2.255, -23.2, -0.86, 0.15, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 3.361, 2.707, -23.8, -0.86, 0.16, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 4.109, 2.74, -23.8, -1.035, 0.19, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 5.303, 3.382, -23.8, -1.209, 0.25, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 6.071, 3.437, -23.8, -1.035, 0.26, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 4.375, 4.852, -23.8, -1.035, 0.18, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, 1.796, 3.794, -23.8, -1.035, 0.24, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\8hu_kultiras_proudmoorekeep_flag02.m2]],
        data = {1, -0.013, 3.311, -22.8, -0.86, 0.13, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 4.703, -0.058, -12.5, -1.209, 0.16, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 4.545, -0.348, -12.5, -2.256, 0.16, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\nodxt\detail\itkfish01.m2]],
        data = {1, 0.405, -2.397, -13, 2.107, 0.41, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion07\doodads\nazjatar\8nzj_creepystarfish_clump_b01.m2]],
        data = {1, -8.609, -3.795, -23.5, -1.034, 0.21, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion06\doodads\murloc\7mu_murloc_food_fish04.m2]],
        data = {1, -1.378, -1.831, -13.1, -0.162, 0.42, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion05\doodads\human\doodads\6hu_fishing_bucket02.m2]],
        data = {1, -1.175, -1.726, -13, 0.886, 0.3, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\azeroth\bootybay\passivedoodad\fishingpoles\fishingpole02.m2]],
        data = {1, -1.059, -1.364, -12.5, -2.779, 0.33, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion04\doodads\pandaren\birds\pa_butterfly_red_loop.m2]],
        data = {1, 3.825, 0.137, -12.5, 2.98, 0.3, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion04\doodads\pandaren\birds\pa_dragonfly_red_loop.m2]],
        data = {1, 1.242, -1.745, -12.5, 2.98, 0.33, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\bird01.m2]],
        data = {1, 0.855, 3.636, -14, -0.161, 0.18, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\bird01.m2]],
        data = {1, -0.83, 2.048, -14, 0.362, 0.07, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\bird01.m2]],
        data = {1, 3.243, 2.991, -14, 1.235, 0.13, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\bird01.m2]],
        data = {1, 3.313, 3.044, -14, 1.933, 0.15, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\bird02.m2]],
        data = {1, -4.663, 2.185, -17.4, 2.98, 0.06, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\bird02.m2]],
        data = {1, -4.733, 2.044, -17.4, -1.907, 0.06, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\bird02.m2]],
        data = {1, -1.131, 2.603, -17.4, -2.605, 0.08, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\birds_condor_01.m2]],
        data = {1, -0.224, 5.393, -16.3, 2.98, 0.1, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\wasp01.m2]],
        data = {1, -6.095, -2.701, -20.5, 2.98, 0.11, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\critter\birds\wasp02.m2]],
        data = {1, 0.062, -2.305, -17.7, -1.034, 0.09, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\cat2large.m2]],
        data = {1, -1.791, -2.355, -14.4, 2.63, 0.35, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\explorersleague\10el_explorersleague_waterskin02.m2]],
        data = {1, -2.154, -1.519, -12.5, 0.711, 0.22, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\explorersleague\10el_explorersleague_stool01.m2]],
        data = {1, -1.649, -1.661, -12.4, 2.456, 0.31, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 5.442, 0.02, -12.5, -1.035, 0.19, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 5.156, -0.048, -12.5, -0.162, 0.15, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\10xp_plant16.m2]],
        data = {1, -6.209, -2.923, -12.5, 2.282, 0.32, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\10xp_plant13.m2]],
        data = {1, 5.365, -0.171, -12.5, 1.932, 0.46, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 4.886, -0.398, -12.5, -1.907, 0.19, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 4.301, -0.144, -12.5, -0.86, 0.14, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 5.961, 0.044, -12.5, -1.558, 0.26, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\10xp_tree17.m2]],
        data = {1, -7.877, -3.489, -15.4, -0.511, 0.26, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\10xp_tree17.m2]],
        data = {1, 5.1, -0.413, -15.4, 1.758, 0.08, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\6ng_foresttreeyoung_b01.m2]],
        data = {1, 6.804, -0.264, -15.2, 1.759, 0.1, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion04\doodads\pandaren\birds\pa_butterfly_red_loop.m2]],
        data = {1, 3.825, 0.137, -12.5, 2.98, 0.3, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\10xp_rock_a02.m2]],
        data = {1, 1.863, -2.947, -16.2, -2.605, 0.15, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\10xp_rock_a02.m2]],
        data = {1, 2.388, -3.013, -16.2, 0.712, 0.14, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\10xp_rock_a02.m2]],
        data = {1, -3.851, -3.076, -16.2, -2.081, 0.19, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\10xp_plant16.m2]],
        data = {1, -6.209, -2.923, -12.5, 2.282, 0.32, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\10xp_plant13.m2]],
        data = {1, -6.679, -2.929, -12.5, -2.78, 0.6, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 4.173, -0.417, -12.5, -2.256, 0.17, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\humanmalekid.m2]],
        data = {1, -0.93, -1.65, -12.5, -2.431, 0.35, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 134, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 4.023, -2.974, -12.5, 2.631, 0.39, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\6ng_aridtree_b03.m2]],
        data = {1, 1.95, -0.298, -1, -0.336, 0.57, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\volcanic\10can_beachfillerbush_b01.m2]],
        data = {1, 4.929, -3.157, -12.5, -0.685, 0.56, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion09\doodads\grasslands\10gsl_foothillsfillerbush_a01.m2]],
        data = {1, 5.534, -2.573, -10, 2.98, 0.84, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[world\expansion06\doodads\hippogryph\7hg_hippogryph_nest02.m2]],
        data = {1, -3.718, -2.958, -14.3, -3.13, 0.14, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 0, 1, 1, camera = 1} },
    { model = SIRUS_LOGIN_PATH ..
        [[interface\glues\models\ui_mainmenu_sirusdefault\duckbaby.m2]],
        data = {1, -3.732, -2.837, -14.4, 0.71, 0.21, 1,
            {1, 0, 0, -0.707, -0.707, 1, 0.7, 0.7, 0.7, 0, 1.0, 1.0, 1.0}, 97, 1, 1, camera = 1} },
} },
}
