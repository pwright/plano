#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import os as _os
import pwd as _pwd
import signal as _signal
import socket as _socket
import sys as _sys
import threading as _threading

try:
    import http.server as _http
except ImportError:
    import BaseHTTPServer as _http

from plano import *

def open_test_session(session):
    if session.module.command.verbose:
        enable_logging(level="debug")

def test_archive_operations(session):
    with working_dir():
        make_dir("some-dir")
        touch("some-dir/some-file")

        make_archive("some-dir")
        assert is_file("some-dir.tar.gz")

        extract_archive("some-dir.tar.gz", output_dir="some-subdir")
        assert is_dir("some-subdir/some-dir")
        assert is_file("some-subdir/some-dir/some-file")

        rename_archive("some-dir.tar.gz", "something-else")
        assert is_file("something-else.tar.gz")

        extract_archive("something-else.tar.gz")
        assert is_dir("something-else")
        assert is_file("something-else/some-file")

def test_dir_operations(session):
    curr_dir = get_current_dir()

    with working_dir("."):
        assert get_current_dir() == curr_dir, (get_current_dir(), curr_dir)

    with working_dir():
        test_dir = make_dir("some-dir")
        test_file = touch(join(test_dir, "some-file"))

        result = list_dir(test_dir)
        assert join(test_dir, result[0]) == test_file, (join(test_dir, result[0]), test_file)

        result = list_dir("some-dir", "*.not-there")
        assert result == [], result

        result = find(test_dir)
        assert result == [test_file], (result, [test_file])

    with working_dir():
        with working_dir("a-dir", quiet=True):
            touch("a-file")

        curr_dir = get_current_dir()
        prev_dir = change_dir("a-dir")
        new_curr_dir = get_current_dir()
        new_prev_dir = change_dir(curr_dir)

        assert curr_dir == prev_dir, (curr_dir, prev_dir)
        assert new_curr_dir == new_prev_dir, (new_curr_dir, new_prev_dir)

def test_env_operations(session):
    result = which("echo")
    assert result, result

    try:
        check_program("not-there")
    except PlanoException:
        pass

    with working_env(SOME_VAR=1):
        assert ENV["SOME_VAR"] == "1", ENV.get("SOME_VAR")

        with working_env(SOME_VAR=2):
            assert ENV["SOME_VAR"] == "2", ENV.get("SOME_VAR")

def test_file_operations(session):
    with working_dir():
        alpha_dir = make_dir("alpha-dir")
        alpha_file = touch(join(alpha_dir, "alpha-file"))
        alpha_link = make_link(join(alpha_dir, "alpha-file-link"), "alpha-file")

        beta_dir = make_dir("beta-dir")
        beta_file = touch(join(beta_dir, "beta-file"))
        beta_link = make_link(join(beta_dir, "beta-file-link"), "beta-file")

        assert exists(beta_link)
        assert exists(beta_file)

        with working_dir("beta-dir"):
            assert exists(read_link("beta-file-link"))

        copied_file = copy(alpha_file, beta_dir)
        assert copied_file == join(beta_dir, "alpha-file"), copied_file

        assert exists(beta_link)
        copied_link = copy(beta_link, join(beta_dir, "beta-file-link-copy"))
        assert copied_link == join(beta_dir, "beta-file-link-copy"), copied_link

        copied_dir = copy(alpha_dir, beta_dir)
        assert copied_dir == join(beta_dir, "alpha-dir"), copied_dir
        assert exists(join(copied_dir, "alpha-file-link"))

        moved_file = move(beta_file, alpha_dir)
        assert moved_file == join(alpha_dir, "beta-file"), moved_file

        moved_dir = move(beta_dir, alpha_dir)
        assert moved_dir == join(alpha_dir, "beta-dir"), moved_dir

        gamma_dir = make_dir("gamma-dir")
        gamma_file = touch(join(gamma_dir, "gamma-file"))

        delta_dir = make_dir("delta-dir")
        delta_file = touch(join(delta_dir, "delta-file"))

        copy(gamma_dir, delta_dir, inside=False)
        assert is_file(join("delta-dir", "gamma-file"))

        move(gamma_dir, delta_dir, inside=False)
        assert is_file(join("delta-dir", "gamma-file"))
        assert not exists(gamma_dir)

        epsilon_dir = make_dir("epsilon-dir")
        epsilon_file_1 = touch(join(epsilon_dir, "epsilon-file-1"))
        epsilon_file_2 = touch(join(epsilon_dir, "epsilon-file-2"))

        result = remove("not-there")
        assert result is None, result

        result = remove(epsilon_file_2)
        assert result == epsilon_file_2, result
        assert not exists(epsilon_file_2)

        result = remove(epsilon_dir)
        assert result == epsilon_dir, result
        assert not exists(epsilon_file_1)
        assert not exists(epsilon_dir)

        input_file = write("zeta-file", "X@replace-me@X")
        output_file = configure_file(input_file, "zeta-file", {"replace-me": "Y"})
        output = read(output_file)
        assert output == "XYX", output

def test_host_operations(session):
    result = get_hostname()
    assert result, result

def test_http_operations(session):
    class Handler(_http.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"[1]")

        def do_POST(self):
            length = int(self.headers["content-length"])
            content = self.rfile.read(length)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(content)

        def do_PUT(self):
            length = int(self.headers["content-length"])
            content = self.rfile.read(length)

            self.send_response(200)
            self.end_headers()

    class ServerThread(_threading.Thread):
        def __init__(self, server):
            _threading.Thread.__init__(self)
            self.server = server

        def run(self):
            self.server.serve_forever()

    host, port = "localhost", get_random_port()
    url = "http://{0}:{1}".format(host, port)
    server = _http.HTTPServer((host, port), Handler)
    server_thread = ServerThread(server)

    server_thread.start()

    try:
        with working_dir():
            result = http_get(url)
            assert result == "[1]", result

            result = http_get(url, insecure=True)
            assert result == "[1]", result

            result = http_get(url, output_file="a")
            output = read("a")
            assert result is None, result
            assert output == "[1]", output

            result = http_get_json(url)
            assert result == [1], result

            file_b = write("b", "[2]")

            result = http_post(url, read(file_b), insecure=True)
            assert result == "[2]", result

            result = http_post(url, read(file_b), output_file="x")
            output = read("x")
            assert result is None, result
            assert output == "[2]", output

            result = http_post_file(url, file_b)
            assert result == "[2]", result

            result = http_post_json(url, parse_json(read(file_b)))
            assert result == [2], result

            file_c = write("c", "[3]")

            result = http_put(url, read(file_c), insecure=True)
            assert result is None, result

            result = http_put_file(url, file_c)
            assert result is None, result

            result = http_put_json(url, parse_json(read(file_c)))
            assert result is None, result
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join()

def test_io_operations(session):
    with working_dir():
        input_ = "some-text\n"
        file_a = write("a", input_)
        output = read(file_a)

        assert input_ == output, (input_, output)

        pre_input = "pre-some-text\n"
        post_input = "post-some-text\n"

        prepend(file_a, pre_input)
        append(file_a, post_input)

        output = tail(file_a, 100)
        tailed = tail(file_a, 1)

        assert output.startswith(pre_input), (output, pre_input)
        assert output.endswith(post_input), (output, post_input)
        assert tailed == post_input, (tailed, post_input)

        input_lines = [
            "alpha\n",
            "beta\n",
            "gamma\n",
        ]

        file_b = write_lines("b", input_lines)
        output_lines = read_lines(file_b)

        assert input_lines == output_lines, (input_lines, output_lines)

        pre_lines = ["pre-alpha\n"]
        post_lines = ["post-gamma\n"]

        prepend_lines(file_b, pre_lines)
        append_lines(file_b, post_lines)

        output_lines = tail_lines(file_b, 100)
        tailed_lines = tail_lines(file_b, 1)

        assert output_lines[0] == pre_lines[0], (output_lines[0], pre_lines[0])
        assert output_lines[4] == post_lines[0], (output_lines[4], post_lines[0])
        assert tailed_lines[0] == post_lines[0], (tailed_lines[0], post_lines[0])

        file_c = touch("c")
        assert is_file(file_c), file_c

def test_json_operations(session):
    with working_dir():
        input_data = {
            "alpha": [1, 2, 3],
        }

        file_a = write_json("a", input_data)
        output_data = read_json(file_a)

        assert input_data == output_data, (input_data, output_data)

        json = read(file_a)
        parsed_data = parse_json(json)
        emitted_json = emit_json(input_data)

        assert input_data == parsed_data, (input_data, parsed_data)
        assert json == emitted_json, (json, emitted_json)

def test_link_operations(session):
    with working_dir():
        make_dir("some-dir")
        path = get_absolute_path(touch("some-dir/some-file"))

        with working_dir("another-dir"):
            link = make_link("a-link", path)
            linked_path = read_link(link)
            assert linked_path == path, (linked_path, path)

def test_logging_operations(session):
    with temp_file() as f:
        disable_logging()

        enable_logging(output=f, level="error")
        enable_logging(output=f, level="notice")
        enable_logging(output=f, level="warn")
        enable_logging(output=f, level="warning")
        enable_logging(output=f, level="debug")

        try:
            try:
                fail("Nooo!")
            except PlanoException:
                pass

            error("Error!")
            warn("Warning!")
            notice("Take a look!")
            debug("By the way")
            debug("abc{0}{1}{2}", 1, 2, 3)
            eprint("Here's a story")
            eprint("About a", "man named Brady")

            exc = Exception("abc123")

            try:
                fail(exc)
            except Exception as e:
                assert e is exc, e

            try:
                exit()
            except SystemExit:
                pass

            try:
                exit("abc")
            except SystemExit:
                pass

            try:
                exit(Exception())
            except SystemExit:
                pass

            try:
                exit(123)
            except SystemExit:
                pass

            try:
                exit(-123)
            except SystemExit:
                pass

            try:
                exit(object())
            except PlanoException:
                pass

            flush()
        except:
            print(read(f))
            raise
        finally:
            enable_logging()

def test_path_operations(session):
    result = get_home_dir()
    assert result == ENV["HOME"], result

    result = get_home_dir("alice")
    assert result.endswith("alice"), result

    with working_dir("/"):
        curr_dir = get_current_dir()
        assert curr_dir == "/", curr_dir

        path = "a/b/c"
        result = get_absolute_path(path)
        assert result == join(curr_dir, path), result

    path = "/x/y/z"
    result = get_absolute_path(path)
    assert result == path, result

    path = "a//b/../c/"
    result = normalize_path(path)
    assert result == "a/c", result

    path = "/a/../c"
    result = get_real_path(path)
    assert result == "/c", result

    path = "/alpha/beta.ext"
    path_split = "/alpha", "beta.ext"
    path_split_extension = "/alpha/beta", ".ext"
    name_split_extension = "beta", ".ext"

    result = join(*path_split)
    assert result == path, result

    result = split(path)
    assert result == path_split, result

    result = split_extension(path)
    assert result == path_split_extension, result

    result = get_parent_dir(path)
    assert result == path_split[0], result

    result = get_base_name(path)
    assert result == path_split[1], result

    result = get_name_stem(path)
    assert result == name_split_extension[0], result

    result = get_name_stem("alpha.tar.gz")
    assert result == "alpha", result

    result = get_name_extension(path)
    assert result == name_split_extension[1], result

    result = get_program_name()
    assert result, result

    result = get_program_name("alpha beta")
    assert result == "alpha", result

    result = get_program_name("X=Y alpha beta")
    assert result == "alpha", result

def test_port_operations(session):
    result = get_random_port()
    assert result >= 49152 and result <= 65535, result

    server_port = get_random_port()
    server_socket = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)

    try:
        server_socket.bind(("localhost", server_port))
        server_socket.listen(5)

        wait_for_port(server_port)
    finally:
        server_socket.close()

    try:
        wait_for_port(str(get_random_port()), timeout=0.1)
    except PlanoException:
        pass

def test_process_operations(session):
    result = get_process_id()
    assert result, result

    proc = run("date")
    assert proc is not None, proc

    print(repr(proc))

    run("date", stash=True)

    proc = run("echo hello", check=False)
    assert proc.exit_code == 0, proc.exit_code

    proc = run("cat /uh/uh", check=False)
    assert proc.exit_code > 0, proc.exit_code

    with temp_file() as temp:
        run("date", output=temp)

    run("date", output=DEVNULL)
    run("date", stdin=DEVNULL)
    run("date", stdout=DEVNULL)
    run("date", stderr=DEVNULL)

    run("echo hello", quiet=True)
    run("echo hello | cat", shell=True)

    try:
        run("/not/there")
    except PlanoException:
        pass

    try:
        run("cat /whoa/not/really", stash=True)
    except PlanoProcessError:
        pass

    result = call("echo hello")
    assert result == "hello\n", result

    result = call("echo hello | cat", shell=True)
    assert result == "hello\n", result

    try:
        call("cat /whoa/not/really")
    except PlanoProcessError:
        pass

    proc = start("echo hello")
    sleep(0.1)
    stop(proc)

    proc = start("sleep 10")
    sleep(0.1)
    kill(proc)
    sleep(0.1)
    stop(proc)

    proc = start("date --not-there")
    sleep(0.1)
    stop(proc)

    with start("sleep 10"):
        sleep(0.1)

    with working_dir():
        touch("i")

        with start("date", stdin="i", stdout="o", stderr="e"):
            pass

def test_string_operations(session):
    result = replace("ab", "a", "b")
    assert result == "bb", result

    result = replace("aba", "a", "b", count=1)
    assert result == "bba", result

    result = nvl(None, "a")
    assert result == "a", result

    result = nvl("b", "a")
    assert result == "b", result

    result = nvl("b", "a", "x{0}x")
    assert result == "xbx", result

    result = shorten("abc", 2)
    assert result == "ab", result

    result = shorten("abc", None)
    assert result == "abc", result

    result = shorten("ellipsis", 6, ellipsis="...")
    assert result == "ell...", result

    result = shorten(None, 6)
    assert result == "", result

    result = plural(None)
    assert result == "", result

    result = plural("")
    assert result == "", result

    result = plural("test")
    assert result == "tests", result

    result = plural("test", 1)
    assert result == "test", result

    result = plural("bus")
    assert result == "busses", result

    result = plural("bus", 1)
    assert result == "bus", result

    encoded_result = base64_encode(b"abc")
    decoded_result = base64_decode(encoded_result)
    assert decoded_result == b"abc", decoded_result

    encoded_result = url_encode("abc=123&yeah!")
    decoded_result = url_decode(encoded_result)
    assert decoded_result == "abc=123&yeah!", decoded_result

    try:
        proc = start("sleep 1")
        default_sigterm_handler(_signal.SIGTERM, None)
    except SystemExit:
        pass
    finally:
        stop(proc)

def test_temp_operations(session):
    temp_dir = get_temp_dir()

    result = make_temp_file()
    assert result.startswith(temp_dir), result

    result = make_temp_file(suffix=".txt")
    assert result.endswith(".txt"), result

    result = make_temp_dir()
    assert result.startswith(temp_dir), result

    with temp_file() as f:
        write(f, "test")

    with working_dir() as d:
        list_dir(d)

    user_temp_dir = get_user_temp_dir()
    assert user_temp_dir, user_temp_dir

    ENV.pop("XDG_RUNTIME_DIR", None)

    user_temp_dir = get_user_temp_dir()
    assert user_temp_dir, user_temp_dir

def test_unique_id_operations(session):
    id1 = get_unique_id()
    id2 = get_unique_id()

    assert id1 != id2, (id1, id2)

    result = get_unique_id(1)
    assert len(result) == 2

    result = get_unique_id(16)
    assert len(result) == 32

def test_user_operations(session):
    user = _pwd.getpwuid(_os.getuid())[0]
    result = get_user()
    assert result == user, (result, user)

def test_plano_command(session):
    from plano import _targets, _default_target

    def invoke(args):
        _targets.clear(); _default_target = None

        command = PlanoCommand()
        command.main(args)

    invoke(["-f", "scripts/test.planofile"])
    invoke(["-f", "scripts/test.planofile", "--quiet"])
    invoke(["-f", "scripts/test.planofile", "--verbose"])
    invoke(["-f", "scripts/test.planofile", "--init-only"])
    invoke(["-f", "scripts/test.planofile", "build"])
    invoke(["-f", "scripts/test.planofile", "install"])
    invoke(["-f", "scripts/test.planofile", "clean"])
    invoke(["-f", "scripts/test.planofile", "run"])
    invoke(["-f", "scripts/test.planofile", "help"])

    try:
        invoke(["-f", "scripts/test.planofile", "no-such-target"])
    except SystemExit:
        pass

    try:
        invoke(["-f", "not/there/at/all"])
    except SystemExit:
        pass

    _targets.clear(); _default_target = None

    @target
    def alpha():
        print("A")

    try:
        @target(name="alpha")
        def another_alpha():
            pass
    except PlanoException:
        pass

    @target(requires=alpha)
    def beta():
        print("B")

    @target(default=True)
    def gamma():
        print("G")

    @target(requires=(beta, gamma))
    def delta():
        print("D")

    command = PlanoCommand()

    with temp_file() as f:
        command.main(["-f", f, "delta"])

    try:
        invoke(["-f" "not/there/at/all"])
    except SystemExit:
        pass