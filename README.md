# multi-engine-query-p3
Run an NXQL Query across multiple Nexthink Engine Appliances.

This documentation is a Work-In-Progress, and will be updated shortly.

To Install, briefly:
1. Create a Nexthink Utility VM (use the base .iso or .vhd file, but don't install as an Engine or Portal)
2. Configure the network and passwords on the Utility VM
3. Create a folder custom/ansible/multi-engine-query-p3
4. Copy the Ansible files there
5. Follow the instructions in the file under docs/
6. Once you've run the Ansible Playbook, you can go to ~/custom/multi-engine-query-p3 and use ./run.sh
