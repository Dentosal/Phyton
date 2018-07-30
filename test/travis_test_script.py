import sys, subprocess, time

"""
This script is made as a wrapper for sc2 bots to set a timeout to the bots (in case they cant find the last enemy structure or the game is ending in a draw)
"""

retries = 10
timeout_time = 2*60



if len(sys.argv) > 1:
    # Attempt to run process with retries and timeouts
    t0 = time.time()
    process, result = None, None
    for i in range(retries):
        t0 = time.time()

        process = subprocess.Popen(["python", sys.argv[1]], stdout=subprocess.PIPE)
        try:
            result = process.communicate(timeout=timeout_time)
        except subprocess.TimeoutExpired:
            continue
        out, err = result
        result = out.decode("utf-8")

        # Break as the bot run was successful
        break


    # Bot was not successfully run in time, returncode will be None
    if process.returncode is None or process.returncode != 0:
        print("Exiting with exit code 5, error: Attempted to launch script {} timed out after {} seconds. Retries completed: {}".format(sys.argv[1], timeout_time, retries))
        exit(5)


    # Reformat the output into a list
    print_output: str = result
    linebreaks = [
        ["\r\n", print_output.count("\r\n")],
        ["\r", print_output.count("\r")],
        ["\n", print_output.count("\n")],
    ]
    most_linebreaks_type = max(linebreaks, key=lambda x: x[1])
    linebreak_type, linebreak_count = most_linebreaks_type
    output_as_list = print_output.split(linebreak_type)


    # process.returncode will always return 0 if the game was run successfully or if there was a python error (in this case it returns as defeat)
    print("Returncode: {}".format(process.returncode))
    print("Game took {} real time seconds".format(round(time.time() - t0, 1)))
    if process is not None and process.returncode == 0:
        for line in output_as_list:
            # This will throw an error if a bot is called Traceback
            if "Traceback " in line:
                print("Exiting with exit code 3, error log:\r\n{}".format(output_as_list))
                exit(3)
        print("Exiting with exit code 0")
        exit(0)

    # Exit code 1: game crashed I think
    print("Exiting with exit code 1")
    exit(1)

# Exit code 2: bot was not launched
print("Exiting with exit code 2")
exit(2)