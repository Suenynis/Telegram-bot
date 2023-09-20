import os

# Function to add an admin ID to the .env file
def add_admin_id(admin_id):
    # Read the existing ADMIN_IDS variable from the .env file
    with open('.env', 'r') as env_file:
        lines = env_file.readlines()

    updated_lines = []
    for line in lines:
        if line.startswith('ADMIN_ID='):
            # Extract the existing admin IDs
            existing_ids = line.strip().split('=')[1]
            existing_ids_list = [id.strip() for id in existing_ids.split(',')]

            # Append the new admin ID (if it's not already present)
            if admin_id not in existing_ids_list:
                existing_ids_list.append(admin_id)

            # Join the updated admin IDs and update the line
            updated_ids = ', '.join(existing_ids_list)
            updated_line = f'ADMIN_ID={updated_ids}\n'
            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)

    # Write the updated lines back to the .env file
    with open('.env', 'w') as env_file:
        env_file.writelines(updated_lines)

# Usage example
new_admin_id = '987654321'  # Replace with the new admin ID you want to add
add_admin_id(new_admin_id)
