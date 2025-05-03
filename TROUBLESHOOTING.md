# Troubleshooting WiseFlow Deployment

## Issue: deploy_and_launch.bat Disappears Instantly

If you're experiencing an issue where the `deploy_and_launch.bat` script window disappears immediately after launching, try the following solutions:

### Solution 1: Use the Wrapper Script

We've created a wrapper script that will help keep the deployment window open:

1. Download both `deploy_and_launch.bat` and `run_deploy.bat` to the same folder
2. Run `run_deploy.bat` instead of directly running `deploy_and_launch.bat`
3. The deployment will start in a new window that will stay open

### Solution 2: Run from Command Prompt

1. Open Command Prompt (Start menu > type "cmd" > press Enter)
2. Navigate to the folder containing the script:
   ```
   cd path\to\your\folder
   ```
3. Run the script directly:
   ```
   deploy_and_launch.bat
   ```

### Solution 3: Run as Administrator

1. Right-click on `deploy_and_launch.bat`
2. Select "Run as administrator"
3. Confirm the User Account Control prompt if it appears

### Solution 4: Create a Shortcut with Special Properties

1. Right-click in the folder containing the script and select New > Shortcut
2. In the location field, enter:
   ```
   cmd.exe /K "deploy_and_launch.bat"
   ```
3. Name the shortcut "Run WiseFlow Deployment"
4. Use this shortcut to run the deployment script

## Common Causes of This Issue

1. **Script Errors**: The script might be encountering an error early in execution
2. **Permission Issues**: The script might not have the necessary permissions
3. **Missing Dependencies**: Required tools like Git or Python might be missing
4. **Antivirus Interference**: Security software might be blocking script execution

## Logging for Troubleshooting

If you continue to experience issues, you can create a log file to help diagnose the problem:

1. Open Command Prompt as Administrator
2. Navigate to the folder containing the script
3. Run the following command:
   ```
   deploy_and_launch.bat > deployment_log.txt 2>&1
   ```
4. Check the `deployment_log.txt` file for error messages

## Still Having Issues?

If you continue to experience problems, please:

1. Create an issue on the GitHub repository with details about your system
2. Include any error messages from the log file
3. Describe the exact steps you're taking to run the script

