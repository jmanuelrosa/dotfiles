function blue
  echo "Running bluetooth services ..."
  sudo systemctl start bluetooth
  blueman-applet > /dev/null 2>&1 &
  echo "Bluetooth is running"
end