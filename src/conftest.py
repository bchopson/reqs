def pytest_configure(config):
    # Any warnings not ignored here should cause pytest to throw an error. It seems like the error
    # setting should go be last in the list, but warnings that match multiple lines will apply the
    # last line matched.
    config.addinivalue_line('filterwarnings', 'error')

    # This sets the root logger level.  Set it to warning by default to keep down the noise on test
    # failures.  Override like --log-level=info.
    config.option.log_level = 'debug'
