-- Select Tarasek for male Drakkin without changing female displays or faction policy.
UPDATE `chrraces_dbc` SET `MaleDisplayId` = 60070
WHERE `ID` = 66
  AND `MaleDisplayId` = 60064;
