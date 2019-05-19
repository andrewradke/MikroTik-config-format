#!/usr/bin/env python3

import sys
import os
import shutil
import re
import time
import getpass


import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--timeout',				help='SSH timeout in seconds, default: 10')
parser.add_argument('-u', '--username',				help='Username for access to RouterOS, default: local username')
parser.add_argument('-b', '--baseurl',				help='Base URL for retrieving RouterOS images if needed, default: https://download.mikrotik.com/routeros/')
parser.add_argument('-n', '--noop',      action="store_true",	help="Don't perform any actions, just report what will occur. Implies --verbose")
parser.add_argument('-v', '--verbose',   action="count",	help='Verbose output')
parser.add_argument('hosts', metavar='HOST', type=str, nargs='+', help='RouterOS host to upgrade')
args = parser.parse_args()

class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'


#pingable = os.system("fping -q localhost")
#if pingable == 127:
#	print("fping is required to be able check for the RouterOS device connectivity after rebooting")
#	sys.exit(1)

if args.username:
	username = args.username
else:
	username = getpass.getuser()

if args.timeout:
	timeout = args.timeout
else:
	timeout = 10

if args.baseurl:
	baseurl = args.baseurl
else:
	baseurl = "https://download.mikrotik.com/routeros/"

if args.noop:
	if not args.verbose:
		args.verbose = 1

if args.verbose:
	print("Verbose output enabled")
	print("Verbose level {}".format(args.verbose))
	print("Username: '{}'".format(username))
	print("Timeout: {} seconds".format(timeout))
	if args.noop:
		print("Dry run only. NOT performing any actions.")

part_line_regex = re.compile('.*\\\$')
next_line_regex = re.compile('^    (?=[^ ])')

processing_errors = False
output = ''

for hostname in args.hosts:
	if args.verbose:
		if sys.stdout.isatty():
			print(bcolors.BOLD + bcolors.UNDERLINE, end='')
		print("*** {} ***".format(hostname), end='')
		if sys.stdout.isatty():
			print(bcolors.ENDC)

	prev_line = ''
	get_next_line = False

	fp = open(hostname, "r")
	line = fp.readline().strip("\r\n")
	while line:
		# If the last line ended in a '\' then this one is a continuation
		# Otherwise use just the lineon it's own
		if get_next_line is True:
			m = next_line_regex.match(line)
			if m:
				line = prev_line + re.sub('^    (?=[^ ])', '', line)
				prev_line = ''
			else:
				print("ERROR: Line doesn't start with exactly 4 spaces: '{}'".format(line))
				processing_errors = True
			get_next_line = False

		m = part_line_regex.match(line)
		if m:
			# We don't have a full line because this one ends in a '\'
			prev_line = re.sub('\\\$', '', line)
			get_next_line = True
		else:
			in_quotes   = False
			in_brackets = False
			skip_space  = False

			# For 'set' lines leave the next value if it doesn't include an '='
			m = re.match('^set [^ =]+ ', line)
			if m:
				skip_space = True

			if line[0] is "/" or line[0] is "#":
				# Keep these lines as is
				output += line + "\n"
			else:
				this_line = ''
				for x in range(len(line)):
					if line[x] is '[':
						in_brackets = True
					elif line[x] is ']':
						in_brackets = False
					elif line[x] is '"':
						if in_quotes is False:
							in_quotes = True
						else:
							in_quotes = False
					elif line[x] is ' ' and skip_space is True:
						# Leave this on the same line as the "set" statement
						skip_space = False
					elif line[x] is ' ' and in_quotes is False and in_brackets is False:
						# Only put three spaces at the beginning of the next line as we'll print the existing space after that
						this_line += " \\\n   "
					# add this character now
					this_line += line[x]
				# Finish with a newline
				output += this_line + "\n"

		# Get the next line to process
		line = fp.readline().strip("\r\n")
	fp.close()

	if processing_errors is True:
		print("Errors found nothing will be changed")
	else:
		if args.noop:
			print(output, end="")
		else:
			fp = open(hostname, "w")
			fp.write(output)
			fp.close()
	output = ''
