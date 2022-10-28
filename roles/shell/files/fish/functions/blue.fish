function blue
  if test "$CURRENT_OS" = "Linux"
    echo "Running bluetooth services ..."
    sudo systemctl start bluetooth
    blueman-applet > /dev/null 2>&1 &
    echo "Bluetooth is running"
  end
end
