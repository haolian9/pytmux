

todo:
* publish as a library
    * rm unnecessary deps, like trio
    * add a setup.py


test cases:

```
# body comes after `%end`

run-shell 'date; sleep 3; date'
%begin 1623138361 111675 1
%end 1623138361 111675 1
Tue Jun  8 03:46:01 PM CST 2021
Tue Jun  8 03:46:04 PM CST 2021
```

```
# output bytes bigger than PIPE_BUF
# which causes `BlockingIOError: write could not complete without blocking`
# in multi-coroutine env

list-keys
```
