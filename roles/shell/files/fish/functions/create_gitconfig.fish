function create_gitconfig --description "Create a .gitconfig file for a company"
  # Prompt the user for the company name
  read -P "Enter the company name: " company_name

  # # Prompt the git user for this company "
  read -P "Enter the git name: " user_name

  # Prompt the user for their email
  read -P "Enter the git email: " user_email

  # Define the paths
  set -l base_dir ~/developer
  set -l company_dir ~/developer/$company_name
  set -l gitconfig_file "$company_dir/.gitconfig.$company_name"

  # Create the directory structure if it doesn't exist
  test -d "$company_dir" || mkdir -p "$company_dir"

  # Write the .gitconfig file
  echo "[user]" > "$gitconfig_file"
  echo "    name = $user_name" >> "$gitconfig_file"
  echo "    email = $user_email" >> "$gitconfig_file"

  # Success message
  echo "Configuration file created at: $gitconfig_file"
end
