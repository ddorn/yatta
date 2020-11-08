{ pkgs? import <nixpkgs> {}, ... }:
with pkgs;

let
  customPython = pkgs.python38.buildEnv.override {
    extraLibs = with pkgs.python38Packages; [
      pygame
      click
      ptpython
    ];
  };
in
  mkShell {
    buildInputs = [
      customPython
      xdotool
    ];
  }
