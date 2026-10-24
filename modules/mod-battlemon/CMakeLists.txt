# Unified Battlemon: collection, battle engine, overworld and pet battles.
# The core recursively collects src/ and calls Addmod_battlemonScripts once.
# Source set includes BattlemonCenter.cpp; changing this file triggers the remote CMake re-glob.
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src")

# Keep existing filenames so remote custom settings continue to load unchanged.
AC_ADD_CONFIG_FILE("${CMAKE_CURRENT_LIST_DIR}/conf/mod_battlemon.conf.dist")
AC_ADD_CONFIG_FILE("${CMAKE_CURRENT_LIST_DIR}/conf/mod_battlemon_overworld.conf.dist")
AC_ADD_CONFIG_FILE("${CMAKE_CURRENT_LIST_DIR}/conf/mod_battlemon_battles.conf.dist")
