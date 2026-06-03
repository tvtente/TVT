App 1816024 output: Traceback (most recent call last):
App 1816024 output:   File "/opt/passenger/src/helper-scripts/wsgi-loader.py", line 384, in <module>
App 1816024 output:     
App 1816024 output: app_module = load_app()
App 1816024 output:  
App 1816024 output:             
App 1816024 output:     ^^^^^^
App 1816024 output: ^^^^
App 1816024 output:   File "/opt/passenger/src/helper-scripts/wsgi-loader.py", line 88, in load_app
App 1816024 output:     
App 1816024 output: spec.loader.exec_module(app_module)
App 1816024 output:   File "<frozen importlib._bootstrap_external>", line 940, in exec_module
App 1816024 output:   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
App 1816024 output:   File "/home/tvtavata/tvt/passenger_wsgi.py", line 1, in <module>
App 1816024 output:     
App 1816024 output: print("SYS.PATH:", sys.path)
App 1816024 output:     
App 1816024 output:            
App 1816024 output:         ^^^
App 1816024 output: NameError: name 'sys' is not defined
App 1816024 output: 
