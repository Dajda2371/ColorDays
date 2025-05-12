alias python=python3
alias pip=pip3

if command -v python &> /dev/null
then
    python ./backend/program.py
else
    ./setup/setup.sh
fi