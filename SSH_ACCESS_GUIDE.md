# SSH Access Guide

## Local Network Access

When you're on the same network as your Raspberry Pi:

```bash
ssh pi@raspberrypi.local
```

Default credentials:
- Username: pi
- Password: raspberry

## Remote Access via Dataplicity

1. Log in to your Dataplicity dashboard
2. Select your device
3. Click "SSH Terminal" to access the web-based terminal

## Securing SSH Access

For better security, it's recommended to:

1. Change the default password:
```bash
passwd
```

2. Use SSH keys instead of passwords:
```bash
# On your local machine
ssh-keygen -t rsa -b 4096
ssh-copy-id pi@raspberrypi.local
```

3. Disable password authentication (after setting up SSH keys):
```bash
sudo nano /etc/ssh/sshd_config
```
Set: `PasswordAuthentication no`
Then restart SSH: `sudo systemctl restart ssh`

## Troubleshooting

1. Check SSH service status:
```bash
sudo systemctl status ssh
```

2. Verify SSH port is open:
```bash
sudo netstat -tuln | grep 22
```

3. Check SSH logs:
```bash
sudo journalctl -u ssh
```

## File Transfers

To copy files to/from your Pi:

```bash
# Copy to Pi
scp localfile.txt pi@raspberrypi.local:~/destination/

# Copy from Pi
scp pi@raspberrypi.local:~/remotefile.txt ./localfile.txt
```

## Using Dataplicity Tunnel

When using Dataplicity:
1. All SSH access is handled through the web terminal
2. No need to configure port forwarding
3. Secure connection is managed by Dataplicity
4. Works from anywhere with internet access