# mrf/tests/Dockerfile
# This file builds the test runner image.

# Start from application image mrf/Dockerfile
# Need to make sure the tag in the build step is matching.
FROM mrf-app:latest

# The WORKDIR and ENV variables are inherited from the base image.

# The source code and tests were copied in the base image,
# so we just defining the command to run the tests.
CMD ["pytest"]
