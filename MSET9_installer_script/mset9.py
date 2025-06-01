#!/usr/bin/python3
import abc, sys, os, platform, time, pathlib, binascii

VERSION = "v2.0"

def prgood(content):
	# print(f"[\033[0;32m✓\033[0m] {content}")
	# so that people aren't confused by the [?]. stupid Windows.
	print(f"[\033[0;32mOK\033[0m] {content}")

def prbad(content):
	print(f"[\033[0;91mXX\033[0m] {content}")

def prinfo(content):
	print(f"[--] {content}")

def cleanup(remount=False):
	pass

def exitOnEnter(errCode = 0, remount=False):
	cleanup(remount)
	input("[--] Enter를 눌러 나가기...")
	exit(errCode)

# wrapper for fs operations. can use pyfilesystem2 directly,
# but try to avoid extra dependency on non-darwin system
class FSWrapper(metaclass=abc.ABCMeta):
	@abc.abstractmethod
	def exists(self, path):
		pass
	@abc.abstractmethod
	def mkdir(self, path):
		pass
	@abc.abstractmethod
	def open(self, path, mode='r'):
		pass
	@abc.abstractmethod
	def getsize(self, path):
		pass
	@abc.abstractmethod
	def remove(self, path):
		pass
	@abc.abstractmethod
	def rename(self, src, dst):
		pass
	@abc.abstractmethod
	def rmtree(self, path):
		pass
	@abc.abstractmethod
	def copytree(self, src, dst):
		pass
	@abc.abstractmethod
	def is_writable(self):
		pass
	@abc.abstractmethod
	def ensurespace(self, size):
		pass
	@abc.abstractmethod
	def close(self):
		pass
	@abc.abstractmethod
	def reload(self):
		pass
	@abc.abstractmethod
	def print_root(self):
		pass

def remove_extra():
	pass

osver = platform.system()
thisfile = os.path.abspath(__file__)
scriptroot = os.path.dirname(thisfile)
systmp = None

def verify_device():
	systemroot = pathlib.Path(sys.executable).anchor # Never hardcode C:. My Windows drive letter is E:, my SD card or USB drive is often C:.
	if os.stat(scriptroot).st_dev == os.stat(systemroot).st_dev:
		prbad("Error 01: 스크립트가 SD 카드 내에서 실행되고 있지 않습니다!")
		prinfo(f"현재 경로: {scriptroot}")
		exitOnEnter()

def dig_for_root():
	import shutil
	global thisfile, scriptroot

	if not os.path.ismount(scriptroot):
		root = scriptroot
		while not os.path.ismount(root) and root != os.path.dirname(root):
			root = os.path.dirname(root)

		for f in ["SafeB9S.bin", "b9", "boot.firm", "boot.3dsx", "boot9strap/", "mset9.py", "MSET9-Windows.bat", "MSET9-macOS.command", "_INSTRUCTIONS.txt", "errors.txt"]:
			try:
				shutil.move(os.path.join(scriptroot, f), os.path.join(root, f))
			except:
				pass # The sanity checks will deal with that. I just don't want the exception to terminate the script.

		with open(os.path.join(scriptroot, "MSET9의 메모.txt"), "w") as f:
			f.write("저기요!\n")
			f.write("모든 MSET9 파일이 SD 카드의 루트로 이동되었습니다.\n\n")

			f.write("\"'SD 카드의 루트'가 무엇인가요...?\"\n")
			f.write("루트는 '어떤 폴더 안에도 없는 것'입니다.\n")
			f.write("'Nintendo 3DS' 폴더를 볼 수 있는 상태입니다. (Nintendo 3DS 폴더 안을 말하는 게 아닙니다!)\n\n")

			f.write("참조 이미지: https://3ds.hacks.guide/images/screenshots/onboarding/sdroot.png\n\n")

			f.write(f"이 글을 쓰는 시점에서는, SD 카드의 루트는 '{root}'입니다. 확인해 보세요!\n")
			f.close()

		scriptroot = root
		thisfile = os.path.join(scriptroot, "mset9.py")

if osver == "Darwin":
	# ======== macOS / iOS? ========

	tmpprefix = "mset9-macos-run-"

	def is_ios():
		machine = os.uname().machine
		return any(machine.startswith(e) for e in ["iPhone", "iPad"])

	def tmp_cleanup():
		global tmpprefix, systmp
		prinfo("임시 폴더 삭제 중...")
		import tempfile, shutil
		if systmp is None:
			systmp = tempfile.gettempdir()
		for dirname in os.listdir(systmp):
			if dirname.startswith(tmpprefix):
				shutil.rmtree(f"{systmp}/{dirname}")
		prinfo("임시 폴더 삭제됨!")

	def run_diskutil_and_wait(command, dev):
		import subprocess
		if type(command) != list:
			command = [command]
		return subprocess.run(["diskutil", *command, dev], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode

	if len(sys.argv) < 2:
		verify_device()
		if not scriptroot.startswith("/Volumes/"): # Can probably remove this now given the above function but meh!
			prbad("Error 01: Nintendo 3DS 폴더를 찾을 수 없습니다! 이 스크립트를 SD 카드의 루트에서 실행하고 있는지 확인해 주세요.")
			# should we add some macos specific message?
			exitOnEnter()

		dig_for_root()
		prinfo("장치 확인 중...")
		device = None
		devid = os.stat(scriptroot).st_dev
		for devname in os.listdir("/dev"):
			if not devname.startswith("disk"):
				continue
			devpath = f"/dev/{devname}"
			if os.stat(devpath).st_rdev == devid:
				device = devpath
				break
		if device is None:
			#prbad("Error :")
			prbad("일치하는 장치를 찾을 수 없습니다, 일어나서는 안될 일인데...")
			exitOnEnter()

		prinfo("이전 임시 폴더 찾는 중...")
		import shutil, tempfile, time
		systmp = tempfile.gettempdir()
		tmpdir = None
		for dirname in os.listdir(systmp):
			if dirname.startswith(tmpprefix):
				dirpath = f"{systmp}/{dirname}"
				script = f"{dirpath}/mset9.py"
				tmp_st = os.stat(script)
				this_st = os.stat(thisfile)
				# hope file size is enough fix... checksum is a bit heavy i assume
				if os.path.exists(script) and tmp_st.st_mtime > this_st.st_mtime and tmp_st.st_size == this_st.st_size:
					tmpdir = dirpath
					break
				else:
					shutil.rmtree(dirpath)
		if tmpdir is None:
			prinfo("임시 폴더 생성 중...")
			tmpdir = tempfile.mkdtemp(prefix=tmpprefix)
			shutil.copyfile(thisfile, f"{tmpdir}/mset9.py")

		prinfo("SD 카드 마운트 해제 시도 중...")
		ret = run_diskutil_and_wait(["umount", "force"], device)

		if ret == 1:
			prbad("Error 16: SD 카드의 마운트 해제를 할 수 없습니다.")
			prinfo("다른 앱이 SD 카드를 사용하고 있진 않은지 확인해주세요.")
			#tmp_cleanup()
			exitOnEnter()

		os.execlp(sys.executable, sys.executable, f"{tmpdir}/mset9.py", device)
		prbad("WTF???")

	device = sys.argv[1]
	if len(sys.argv) == 3:
		systmp = sys.argv[2]
	if not os.path.exists(device):
		prbad("Error 13: 장치가 존재하지 않습니다.")
		prinfo("SD 카드가 제대로 삽입되었는지 확인하세요.")
		prinfo("또한, 디스크 유틸리티에서 SD 카드 자체를 꺼내지 말고, 파티션만 마운트 해제하세요.")
		#tmp_cleanup()
		exitOnEnter()

	# auto venv
	venv_path = os.path.dirname(thisfile)
	venv_bin = f"{venv_path}/bin"
	venv_py = f"{venv_bin}/python3"

	def check_ios_py_entitlement(path):
		import subprocess
		import xml.etree.ElementTree as ET
		try:
			result = subprocess.run(["ldid", "-e", path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
			if result.returncode != 0:
				prbad("Error #:  venv python ios 권한 확인에 실패했습니다.")
				prinfo(f"ldid error (ret={result.returncode})")
				tmp_cleanup()
				exitOnEnter()
				#return False
			tree = ET.fromstring(result.stdout)
			result = 0  # 0: not found    1: wait key
			for child in tree.find("./dict"):
				if child.tag == "key" and child.text == "com.apple.private.security.disk-device-access":
					result = 1
				elif result == 0:
					if child.tag == "true":
						result = True
						break
					elif child.tag == "false":
						result = False
						break
					else:
						result = 0  # not valid, reset

			if result == 0 or result == 1:
				return False

			return result

		except FileNotFoundError:
			return None

	def fix_ios_py_entitlement(path):
		import subprocess

		basepath = os.path.dirname(path)

		if os.path.islink(path):
			import shutil
			realpy = os.path.join(basepath, os.readlink(path))
			os.remove(path)
			shutil.copyfile(realpy, path)
			shutil.copymode(realpy, path)

		entaddxml = os.path.join(basepath, "entadd.xml")
		with open(entaddxml, "w") as f:
			f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
			f.write('<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n')
			f.write('<plist version="1.0">\n')
			f.write('<dict>\n')
			f.write('\t<key>com.apple.private.security.disk-device-access</key>\n')
			f.write('\t<true/>\n')
			f.write('</dict>\n')
			f.write('</plist>\n')

		try:
			args = ["ldid", "-M", f"-S{entaddxml}", path]
			result = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
			if result.returncode != 0:
				prbad("Error #: venv python ios 권한 수정에 실패했습니다.")
				prinfo(f"ldid ret={result.returncode}")
				prinfo("Message:")
				prinfo(result.stderr)

		except FileNotFoundError:
			prbad("Error #: venv python ios 권한을 수정하는 데 실패했습니다.")
			prinfo("뭐죠? ldid가 사라졌나요?")
			tmp_cleanup()
			exitOnEnter()

	def activate_venv():
		global venv_path, venv_bin, venv_py, device, systmp
		import site

		# assuming it's fine if ldid doesn't exist
		if is_ios() and check_ios_py_entitlement(venv_py) == False:
			prinfo("권한 수정 중...")
			fix_ios_py_entitlement(venv_py)

		os.environ["PATH"] = os.pathsep.join([venv_bin, *os.environ.get("PATH", "").split(os.pathsep)])
		os.environ["VIRTUAL_ENV"] = venv_path
		os.environ["VIRTUAL_ENV_PROMPT"] = "(mset9)"

		#if systmp is None:
		#	os.execlp(py_exec, venv_py, __file__, device)
		#else:
		#	os.execlp(py_exec, venv_py, __file__, device, systmp)

		prev_length = len(sys.path)
		ver = sys.version_info
		ver_path = f"python{ver.major}.{ver.minor}"
		path = os.path.realpath(os.path.join(venv_path, "lib", ver_path, "site-packages"))
		site.addsitedir(path)
		sys.path[:] = sys.path[prev_length:] + sys.path[0:prev_length]
		sys.real_prefix = sys.prefix
		sys.prefix = venv_path

	def setup_venv():
		import venv, subprocess
		if "VIRTUAL_ENV" not in os.environ:
			if os.path.exists(venv_bin):
				import shutil
				shutil.rmtree(venv_bin)
			venv.create(venv_path, with_pip=True)
		subprocess.run([venv_py, "-mensurepip"], cwd=venv_path)
		subprocess.run([venv_py, "-mpip", "install", "pyfatfs"], cwd=venv_path)
		activate_venv()

	if "VIRTUAL_ENV" not in os.environ:
		if os.path.exists(venv_py):
			prinfo("venv 찾음, 활성화 하세요...")
			activate_venv()
		elif is_ios():
			have_perm = check_ios_py_entitlement(sys.executable)
			if have_perm == None:
				prinfo("ldid를 찾을 수 없습니다, 설치된 Python에 적절한 권한이 있다고 가정하고 진행합니다.")
				prinfo("만약 실패하게 되면, ldid를 설치하거나 Python을 수동으로 고쳐보세요")
				prinfo("(필요 권한 com.apple.private.security.disk-device-access)")
			elif not have_perm:
				prinfo("권한 수정이 필요하여, venv를 세팅하여 자동으로 고치는 중입니다...")
				setup_venv()

	try:
		from pyfatfs.PyFatFS import PyFatFS
	except ModuleNotFoundError:
		prinfo("PyFatFS를 찾을 수 없습니다. venv를 세팅하여 자동으로 설치하는 중입니다...")
		setup_venv()
		from pyfatfs.PyFatFS import PyFatFS

	# self elevate
	if os.getuid() != 0:
		# run with osascript won't have raw disk access by default...
		# thanks for the perfect security of macos
		#args = [sys.executable, thisfile, device]
		#escaped_args = map(lambda x: f"\\\"{x}\\\"", args)
		#cmd = " ".join(escaped_args)
		#osascript = " ".join([
		#	f"do shell script \"{cmd}\"",
		#	"with administrator privileges",
		#	"without altering line endings"
		#])
		#try:
		#	os.execlp("osascript", "osascript", "-e", osascript)
		prinfo("메시지가 나타나면 컴퓨터의 비밀번호를 입력하세요..")
		prinfo("(타이핑하는 동안에는 아무것도 표시되지 않습니다. 그냥 타이핑하세요.)")
		try:
			import tempfile
			os.execlp("sudo", "sudo", sys.executable, thisfile, device, tempfile.gettempdir())
		except:
			prbad("Error 17: 루트 권한이 필요합니다.")
			#tmp_cleanup()
			exitOnEnter(remount=True)

	from pyfatfs.PyFatFS import PyFatFS
	from pyfatfs.FATDirectoryEntry import FATDirectoryEntry, make_lfn_entry
	from pyfatfs.EightDotThree import EightDotThree
	from pyfatfs._exceptions import PyFATException, NotAnLFNEntryException
	import struct, errno

	def _search_entry(self, name):
		name = name.upper()
		dirs, files, _ = self.get_entries()
		for entry in dirs+files:
			try:
				if entry.get_long_name().upper() == name:
					return entry
			except NotAnLFNEntryException:
				pass
			if entry.get_short_name() == name:
				return entry

		raise PyFATException(f'Cannot find entry {name}',
							 errno=errno.ENOENT)
	FATDirectoryEntry._search_entry = _search_entry

	def make_8dot3_name(dir_name, parent_dir_entry):
		dirs, files, _ = parent_dir_entry.get_entries()
		dir_entries = [e.get_short_name() for e in dirs + files]
		extsep = "."
		def map_chars(name: bytes) -> bytes:
			_name: bytes = b''
			for b in struct.unpack(f"{len(name)}c", name):
				if b == b' ':
					_name += b''
				elif ord(b) in EightDotThree.INVALID_CHARACTERS:
					_name += b'_'
				else:
					_name += b
			return _name
		dir_name = dir_name.upper()
		# Shorten to 8 chars; strip invalid characters
		basename = os.path.splitext(dir_name)[0][0:8].strip()
		if basename.isascii():
			basename = basename.encode("ascii", errors="replace")
			basename = map_chars(basename).decode("ascii")
		else:
			basename = "HAX8D3FN"
		# Shorten to 3 chars; strip invalid characters
		extname = os.path.splitext(dir_name)[1][1:4].strip()
		if basename.isascii():
			extname = extname.encode("ascii", errors="replace")
			extname = map_chars(extname).decode("ascii")
		elif len(extname) != 0:
			extname = "HAX"
		if len(extname) == 0:
			extsep = ""
		# Loop until suiting name is found
		i = 0
		while len(str(i)) + 1 <= 7:
			if i > 0:
				maxlen = 8 - (1 + len(str(i)))
				basename = f"{basename[0:maxlen]}~{i}"
			short_name = f"{basename}{extsep}{extname}"
			if short_name not in dir_entries:
				return short_name
			i += 1
		raise PyFATException("Cannot generate 8dot3 filename, "
							 "unable to find suiting short file name.",
							 errno=errno.EEXIST)
	EightDotThree.make_8dot3_name = staticmethod(make_8dot3_name)

	class FatFS(FSWrapper):
		def __init__(self, device):
			self.device = device
			self.reload()
		def exists(self, path):
			return self.fs.exists(path)
		def isdir(self, path):
			return self.fs.getinfo(path).is_dir
		def mkdir(self, path):
			self.fs.makedir(path)
		def open(self, path, mode='r'):
			return self.fs.open(path, mode)
		def getsize(self, path):
			return self.fs.getsize(path)
		def remove(self, path):
			self.fs.remove(path)
		def rename(self, src, dst):
			srcdir, srcname = f"/{src}".rstrip("/").rsplit("/", 1)
			dstdir, dstname = f"/{dst}".rstrip("/").rsplit("/", 1)
			if srcdir == dstdir and all(not EightDotThree.is_8dot3_conform(n) for n in [srcname, dstname]):
				# cursed rename, lfn and same folder only
				pdentry = self.fs._get_dir_entry(srcdir)
				dentry = pdentry._search_entry(srcname)
				lfn_entry = make_lfn_entry(dstname, dentry.name)
				dentry.set_lfn_entry(lfn_entry)
				self.fs.fs.update_directory_entry(pdentry)
				self.fs.fs.flush_fat()
			elif self.fs.getinfo(src).is_dir:
				self.fs.movedir(src, dst, create=True)
			else:
				self.fs.move(src, dst, create=True)
		def rmtree(self, path):
			self.fs.removetree(path)
		def copytree(self, src, dst):
			self.fs.copydir(src, dst, create=True)
		def listdir(self, path):
			return self.fs.listdir(path)
		def is_writable(self):
			try:
				with self.open("test.txt", "w") as f:
					f.write("test")
					f.close()
				self.remove("test.txt")
				return True
			except:
				return False
		def ensurespace(self, size):
			try:
				first = self.fs.fs.allocate_bytes(size)[0]
				self.fs.fs.free_cluster_chain(first)
				return True
			except PyFATException:
				return False
		def close(self):
			try:
				self.fs.close()
			except AttributeError:
				pass
		def reload(self):
			self.close()
			self.fs = PyFatFS(filename=self.device)
		def print_root(self):
			pass

	try:
		fs = FatFS(device)
	except PyFATException as e:
		msg = str(e)
		if "Cannot open" in msg:
			prbad("Error 14: 장치를 열 수 없습니다.")
			prinfo("디스크 유틸리티에서 SD 카드가 마운트 해제되었는지 확인하세요.")
			if is_ios():
				prinfo("또한 ios 권한 문제일 수 있습니다")
				prinfo("ldid를 설치하거나 Python을 수동으로 고쳐주세요")
				prinfo("(필요 권한 com.apple.private.security.disk-device-access)")
		elif "Invalid" in msg or "bytes per sector" in msg:
			prbad("Error 15: FAT32로 포맷되지 않았거나 잘못된 파일 시스템입니다.")
			prinfo("SD 카드가 알맞게 포맷되었는지 확인해주세요")
			prinfo("찾기: https://wiki.hacks.guide/wiki/Formatting_an_SD_card")
		#tmp_cleanup()
		exitOnEnter()

	def remove_extra():
		tmp_cleanup()

	def cleanup(remount=False):
		global fs, device
		fs.close()
		if remount and not is_ios():
			prinfo("SD 카드 재마운트 시도 중...")
			run_diskutil_and_wait("mount", device)
		#tmp_cleanup()


else:
	# ======== Windows / Linux ========
	import shutil

	class OSFS(FSWrapper):
		def __init__(self, root):
			self.root = root
			self.reload()
		def abs(self, path):
			return os.path.join(self.root, path)
		def exists(self, path):
			return os.path.exists(self.abs(path))
		def isdir(self, path):
			return os.path.isdir(self.abs(path))
		def mkdir(self, path):
			os.mkdir(self.abs(path))
		def open(self, path, mode='r'):
			return open(self.abs(path), mode)
		def getsize(self, path):
			return os.path.getsize(self.abs(path))
		def remove(self, path):
			os.remove(self.abs(path))
		def rename(self, src, dst):
			os.rename(self.abs(src), self.abs(dst))
		def rmtree(self, path):
			shutil.rmtree(self.abs(path))
		def copytree(self, src, dst):
			shutil.copytree(self.abs(src), self.abs(dst))
		def listdir(self, path):
			return os.listdir(path)
		def is_writable(self):
			writable = os.access(self.root, os.W_OK)
			try: # Bodge for windows
				with open("test.txt", "w") as f:
					f.write("test")
					f.close()
				os.remove("test.txt")
			except:
				writable = False
			return writable
		def ensurespace(self, size):
			return shutil.disk_usage(self.root).free >= size
		def close(self):
			pass
		def reload(self):
			try:
				os.chdir(self.root)
			except Exception:
				prbad("Error 08: 작업 디렉토리를 다시 적용할 수 없습니다. SD 카드를 재삽입했나요?")
				exitOnEnter()
		def print_root(self):
			prinfo(f"현재 경로: {self.root}")

	verify_device()
	dig_for_root()
	fs = OSFS(scriptroot)

def clearScreen():
	if osver == "Windows":
		os.system("cls")
	else:
		os.system("clear")

# -1: Cancelled
def getInput(options):
	if type(options) == range:
		options = [*options, (options[-1] + 1)]

	while 1:
		try:
			opt = int(input(">>> "))
		except KeyboardInterrupt:
			print()
			return -1
		except EOFError:
			print()
			return -1
		except ValueError:
			opt = 0xFFFFFFFF

		if opt not in options:
			prbad(f"잘못된 입력입니다, 다시 시도하세요. 잘못된 입력: {str.join(', ', (str(i) for i in options))}")
			continue

		return opt

# Section: insureRoot
if not fs.exists("Nintendo 3DS/"):
	prbad("Error 01: Nintendo 3DS 폴더를 찾을 수 없습니다! 이 스크립트를 SD 카드의 루트에서 실행하고 있는지 확인해주세요.")
	prbad("그래도 문제가 해결되지 않으면, SD 카드를 꺼낸 후 콘솔에 다시 넣고, 콘솔을 껐다가 다시 켠 후, 이 스크립트를 다시 실행해 보세요.")
	fs.print_root()
	exitOnEnter()

# Section: sdWritable
def writeProtectCheck():
	global fs
	prinfo("SD 카드가 쓰기 가능한지 확인 중...")
	if not fs.is_writable():
		prbad("Error 02: SD 카드가 쓰기 금지되어 있습니다! 풀 사이즈 SD 카드를 사용하고 있다면, 잠금 스위치가 위로 향해 있는지 확인해주세요.")
		prinfo("시각 자료: https://nintendohomebrew.com/assets/img/nhmemes/sdlock.png")
		exitOnEnter()
	else:
		prgood("SD 카드가 쓰기 가능합니다!")

# Section: SD card free space
# ensure 16MB free space
if not fs.ensurespace(16 * 1024 * 1024):
	#prbad(f"Error 06: You need at least 16MB free space on your SD card, you have {(freeSpace / 1000000):.2f} bytes!")
	prbad("Error 06: You need at least 16MB free space on your SD card!")
	prinfo("Please free up some space and try again.")
	exitOnEnter()

clearScreen()
print(f"MSET9 {VERSION} SETUP by zoogie, Aven, DannyAAM and thepikachugamer - 한국어 번역 lkdjfalnnlvz")
print("당신의 콘솔 버전과 모델은 무엇인가요?")
print("구형 3DS는 트리거 버튼이 두 개 있습니다 (L과 R)")
print("New 3DS는 트리거 버튼이 네 개 있습니다 (L, R, ZL, ZR)")

print("\n-- Please type in a number then hit return --\n")

consoleNames = {
	1: "구형 3DS/2DS, 11.8.0부터 11.17.0",
	2: "New 3DS/2DS, 11.8.0부터 11.17.0",
	3: "구형 3DS/2DS, 11.4.0부터 11.7.0",
	4: "New 3DS/2DS, 11.4.0부터 11.7.0"
}

print("저 4개의 숫자 중 하나를 입력해주세요!")
for i in consoleNames:
	print(f"{consoleNames[i]}은(는) {i}을(를) 입력해주세요.")

# print("Enter 1 for: Old 3DS/2DS, 11.8.0 to 11.17.0")
# print("Enter 2 for: New 3DS/2DS, 11.8.0 to 11.17.0")
# print("Enter 3 for: Old 3DS/2DS, 11.4.0 to 11.7.0")
# print("Enter 4 for: New 3DS/2DS, 11.4.0 to 11.7.0")

encodedID1s = {
	1: "FFFFFFFA119907488546696508A10122054B984768465946C0AA171C4346034CA047B84700900A0871A0050899CE0408730064006D00630000900A0862003900",
	2: "FFFFFFFA119907488546696508A10122054B984768465946C0AA171C4346034CA047B84700900A0871A005085DCE0408730064006D00630000900A0862003900",
	3: "FFFFFFFA119907488546696508A10122054B984768465946C0AA171C4346034CA047B84700900A08499E050899CC0408730064006D00630000900A0862003900",
	4: "FFFFFFFA119907488546696508A10122054B984768465946C0AA171C4346034CA047B84700900A08459E050881CC0408730064006D00630000900A0862003900"
}

consoleIndex = getInput(range(1, 4))
if consoleIndex < 0:
	prgood("Goodbye!")
	exitOnEnter(remount=True)

ID0, ID0Count, ID1, ID1Count = "", 0, "", 0

haxStates = ["\033[30;1mID1이 생성되지 않았습니다\033[0m", "\033[33;1m준비 안됨 - 자세한 내용은 MSET9 상태를 확인하세요.\033[0m", "\033[32m준비됨\033[0m", "\033[32;1m주입됨\033[0m", "\033[32m트리거 파일 삭제됨\033[0m"]
haxState = 0

realID1Path = ""
realID1BackupTag = "_user-id1"

hackedID1 = bytes.fromhex(encodedID1s[consoleIndex]).decode("utf-16le")  # ID1 - arm injected payload in readable format
hackedID1Path = ""

homeMenuExtdata = [0x8F,  0x98,  0x82,  0xA1,  0xA9,  0xB1]  # us,eu,jp,ch,kr,tw
miiMakerExtdata = [0x217, 0x227, 0x207, 0x267, 0x277, 0x287]  # us,eu,jp,ch,kr,tw
trigger = "002F003A.txt"  # all 3ds ":/" in hex format
triggerFilePath = ""

def createHaxID1():
	global fs, ID0, hackedID1Path, realID1Path, realID1BackupTag

	print("\033[0;33m=== 부연 설명 ===\033[0m") # 5;33m? The blinking is awesome but I also don't want to frighten users lol
	print()
	print("이 과정은 당신의 3DS 데이터를 일시적으로 초기화합니다.")
	print("설치한 모든 앱과 테마가 사라질 것입니다.")
	print("이는 완전히 정상적인 현상이며, 모든 것이 제대로 진행된다면,")
	print("마무리 과정에서 다시 나타날 것입니다.")
	print()
	print("어떤 경우든 SD 카드의 내용을 PC의 폴더에 백업하는 것을 강력히 권장합니다.")
	print("(특히 'Nintendo 3DS' 폴더)")
	print()

	if osver == "Linux": # ...
		print("(Linux에선, 제대로 진행되지 않을 수 있습니다 - SD 카드가 'utf8' 옵션으로 마운트되어 있는지 확인해 주세요.)")
		print()

	print("'1'을 다시 입력해 확인")
	print("'2'를 입력하여 취소")
	time.sleep(3)
	if getInput(range(1, 2)) != 1:
		print()
		prinfo("취소되었습니다.")
		exitOnEnter(remount=True)

	hackedID1Path = ID0 + "/" + hackedID1

	try:
		prinfo("해킹된 ID1 생성 중...")
		fs.mkdir(hackedID1Path)
		prinfo("더미 데이터베이스 생성 중...")
		fs.mkdir(hackedID1Path + "/dbs")
		fs.open (hackedID1Path + "/dbs/title.db", "w").close()
		fs.open (hackedID1Path + "/dbs/import.db", "w").close()
	except Exception as exc:
		if isinstance(exc, OSError) and osver == "Windows" and exc.winerror == 234: # WinError 234 my love
			prbad("Error 18: Windows 로캘 설정이 망가졌습니다!")
			prinfo("https://3ds.hacks.guide/troubleshooting-mset9.html 에서 설명을 확인하세요.")
			prinfo("도움이 필요하다면, Discord의 Nintendo Homebrew 채널에 가입하세요: https://discord.gg/nintendohomebrew")
		elif isinstance(exc, OSError) and osver == "Linux" and exc.errno == 22: # Don't want this message to display on Windows if it ever manages to
			prbad("해킹된 ID1을 생성하는데 실패했습니다!") # Give this an error number?
			prbad(f"에러 세부 사항: {str(exc)}")
			prinfo("SD 카드를 마운트 해제하고 'utf8' 옵션으로 다시 마운트해 보세요.") # Should we do this ourself? Like look at macOS
		else:
			prbad("알 수 없는 오류가 발생했습니다!")
			prbad(f"에러 세부 사항: {str(exc)}")
			prinfo("도움을 위해선 Discord의 Nintendo Homebrew 채널에 가입하세요: https://discord.gg/nintendohomebrew")

		exitOnEnter()

	if not realID1Path.endswith(realID1BackupTag):
		prinfo("기존 ID1 백업 중...")
		fs.rename(realID1Path, realID1Path + realID1BackupTag)

	prgood("해킹된 ID1 생성 완료.")
	exitOnEnter()

titleDatabasesGood = False
menuExtdataGood = False
miiExtdataGood = False

def sanity():
	global fs, hackedID1Path, titleDatabasesGood, menuExtdataGood, miiExtdataGood

	prinfo("데이터베이스 생성 중중...")
	checkTitledb  = softcheck(hackedID1Path + "/dbs/title.db",  0x31E400)
	checkImportdb = softcheck(hackedID1Path + "/dbs/import.db", 0x31E400)
	titleDatabasesGood = not (checkTitledb or checkImportdb)
	if not titleDatabasesGood:
		if not fs.exists(hackedID1Path + "/dbs"):
			fs.mkdir(hackedID1Path + "/dbs")
		# Stub them both. I'm not sure how the console acts if title.db is fine but not import. Someone had that happen, once
		fs.open(hackedID1Path + "/dbs/title.db",  "w").close()
		fs.open(hackedID1Path + "/dbs/import.db", "w").close()

	prinfo("HOME 메뉴 추가 데이터 확인 중...")
	for i in homeMenuExtdata:
		extdataRegionCheck = hackedID1Path + f"/extdata/00000000/{i:08X}"
		if fs.exists(extdataRegionCheck):
			menuExtdataGood = True
			break
	
	prinfo("Mii 스튜디오 추가 데이터 확인 중...")
	for i in miiMakerExtdata:
		extdataRegionCheck = hackedID1Path + f"/extdata/00000000/{i:08X}"
		if fs.exists(extdataRegionCheck):
			miiExtdataGood = True
			break

	return menuExtdataGood and miiExtdataGood and titleDatabasesGood

def sanityReport():
	fs.print_root()

	if not menuExtdataGood:
		prbad("HOME menu extdata: Missing!")
		prinfo("Please power on your console with your SD inserted, then check again.")
		prinfo("If this does not work, your SD card may need to be reformatted.")
	else:
		prgood("HOME menu extdata: OK!")

	print()

	if not miiExtdataGood:
		prbad("Mii Maker extdata: Missing!")
		prinfo("Please power on your console with your SD inserted, then launch Mii Maker.")
	else:
		prgood("Mii Maker extdata: OK!")

	print()

	if not titleDatabasesGood:
		prbad("Title database: Not initialized!")
		prinfo("Please power on your console with your SD inserted, open System Setttings,")
		prinfo("navigate to Data Management -> Nintendo 3DS -> Software, then select Reset.")
	else:
		prgood("Title database: OK!")

	print()

def injection(create=True):
	global fs, haxState, hackedID1Path, trigger

	triggerFilePath = hackedID1Path + "/extdata/" + trigger

	if not fs.exists(triggerFilePath) ^ create:
		prbad(f"Trigger file already {'injected' if create else 'removed'}!")
		return

	if fs.exists(triggerFilePath):
		fs.remove(triggerFilePath)
		haxState = 4
		prgood("Removed trigger file.")
		return

	prinfo("Injecting trigger file...")
	with fs.open(triggerFilePath, 'w') as f:
		f.write("pls be haxxed mister arm9, thx")
		f.close()

	prgood("MSET9 successfully injected!")
	exitOnEnter()

def remove():
	global fs, ID0, ID1, hackedID1Path, realID1Path, realID1BackupTag, titleDatabasesGood

	prinfo("Removing MSET9...")

	if hackedID1Path and fs.exists(hackedID1Path):
		if not fs.exists(realID1Path + "/dbs") and titleDatabasesGood:
			prinfo("Moving databases to user ID1...")
			fs.rename(hackedID1Path + "/dbs", realID1Path + "/dbs")

		prinfo("Deleting hacked ID1...")
		fs.rmtree(hackedID1Path)

	if fs.exists(realID1Path) and realID1Path.endswith(realID1BackupTag):
		prinfo("Renaming original ID1...")
		fs.rename(realID1Path, ID0 + "/" + ID1[:32])
		ID1 = ID1[:32]
		realID1Path = ID0 + "/" + ID1

	haxState = 0
	prgood("Successfully removed MSET9!")

def softcheck(keyfile, expectedSize = None, crc32 = None):
	global fs
	filename = keyfile.rsplit("/")[-1]

	if not fs.exists(keyfile):
		prbad(f"{filename} does not exist on SD card!")
		return 1

	fileSize = fs.getsize(keyfile)
	if not fileSize:
		prbad(f"{filename} is an empty file!")
		return 1
	elif expectedSize and fileSize != expectedSize:
		prbad(f"{filename} is size {fileSize:,} bytes, not expected {expectedSize:,} bytes")
		return 1

	if crc32:
		with fs.open(keyfile, "rb") as f:
			checksum = binascii.crc32(f.read())
			f.close()
			if crc32 != checksum:
				prbad(f"{filename} was not recognized as the correct file")
				return 1

	prgood(f"{filename} looks good!")
	return 0

def is3DSID(name):
	if not len(name) == 32:
		return False

	try:
		hex_test = int(name, 0x10)
	except:
		return False

	return True


# Section: Sanity checks A (global files required for exploit)
writeProtectCheck()

prinfo("Ensuring extracted files exist...")

fileSanity = 0
fileSanity += softcheck("boot9strap/boot9strap.firm", crc32=0x08129C1F)
fileSanity += softcheck("boot.firm")
fileSanity += softcheck("boot.3dsx")
fileSanity += softcheck("b9")
fileSanity += softcheck("SafeB9S.bin")

if fileSanity > 0:
	prbad("Error 07: One or more files are missing or malformed!")
	prinfo("Please re-extract the MSET9 zip file, overwriting any existing files when prompted.")
	exitOnEnter()

# prgood("All files look good!")

# Section: sdwalk
for dirname in fs.listdir("Nintendo 3DS/"):
	fullpath = "Nintendo 3DS/" + dirname

	if not fs.isdir(fullpath):
		prinfo(f"Found file in Nintendo 3DS folder? '{dirname}'")
		continue

	if not is3DSID(dirname):
		continue

	prinfo(f"Detected ID0: {dirname}")
	ID0 = fullpath
	ID0Count += 1

if ID0Count != 1:
	prbad(f"Error 04: You don't have 1 ID0 in your Nintendo 3DS folder, you have {ID0Count}!")
	if ID0Count == 0:
		prinfo("Do not manually create the \"Nintendo 3DS\" folder. Delete the folder for now: the guide will create it on its own.")
	else:
		prinfo("Consult: https://3ds.hacks.guide/troubleshooting-mset9.html for help!")
	exitOnEnter()

for dirname in fs.listdir(ID0):
	fullpath = ID0 + "/" + dirname

	if not fs.isdir(fullpath):
		prinfo(f"Found file in ID0 folder? '{dirname}'")
		continue

	if is3DSID(dirname) or (dirname[32:] == realID1BackupTag and is3DSID(dirname[:32])):
		prinfo(f"Detected ID1: {dirname}")
		ID1 = dirname
		realID1Path = ID0 + "/" + ID1
		ID1Count += 1
	elif "sdmc" in dirname and len(dirname) == 32:
		currentHaxID1enc = dirname.encode("utf-16le").hex().upper()
		currentHaxID1index = 0

		for haxID1index in encodedID1s:
			if currentHaxID1enc == encodedID1s[haxID1index]:
				currentHaxID1index = haxID1index
				break

		if currentHaxID1index == 0 or (hackedID1Path and fs.exists(hackedID1Path)): # shouldn't happen
			prbad("Unrecognized/duplicate hacked ID1 in ID0 folder, removing!")
			fs.rmtree(fullpath)
		elif currentHaxID1index != consoleIndex:
			prbad("Error 03: Don't change console model/version in the middle of MSET9!")
			print(f"Earlier, you selected: '[{currentHaxID1index}.] {consoleNames[currentHaxID1index]}'")
			print(f"Now, you selected:     '[{consoleIndex}.] {consoleNames[consoleIndex]}'")
			print()
			print("Please re-enter the number for your console model and version.")

			choice = getInput([consoleIndex, currentHaxID1index])
			if choice < 0:
				prinfo("Cancelled.")
				hackedID1Path = fullpath
				remove()
				exitOnEnter()

			elif choice == currentHaxID1index:
				consoleIndex = currentHaxID1index
				hackedID1 = dirname

			elif choice == consoleIndex:
				fs.rename(fullpath, ID0 + "/" + hackedID1)

		hackedID1Path = ID0 + "/" + hackedID1
		sanityOK = sanity()

		if fs.exists(hackedID1Path + "/extdata/" + trigger):
			triggerFilePath = hackedID1Path + "/extdata/" + trigger
			haxState = 3 # Injected.
		elif sanityOK:
			haxState = 2 # Ready!
		else:
			haxState = 1 # Not ready...

if ID1Count != 1:
	prbad(f"Error 05: You don't have 1 ID1 in your Nintendo 3DS folder, you have {ID1Count}!")
	prinfo("Consult: https://3ds.hacks.guide/troubleshooting-mset9.html for help!")
	exitOnEnter()

def mainMenu():
	clearScreen()
	print(f"MSET9 {VERSION} SETUP by zoogie, Aven, DannyAAM and thepikachugamer")
	print(f"Using {consoleNames[consoleIndex]}")
	print()
	print(f"Current MSET9 state: {haxStates[haxState]}")

	print("\n-- Please type in a number then hit return --\n")

	print("↓ Input one of these numbers!")

	print("1. Create MSET9 ID1")
	print("2. Check MSET9 status")
	print("3. Inject trigger file")
	print("4. Remove trigger file")

	if haxState != 3:
		print("5. Remove MSET9")

	print("\n0. Exit")

	while 1:
		optSelect = getInput(range(0, 5))

		fs.reload() # (?)

		if optSelect <= 0:
			break

		elif optSelect == 1: # Create hacked ID1
			if haxState > 0:
				prinfo("Hacked ID1 already exists.")
				continue
			createHaxID1()
			exitOnEnter()

		elif optSelect == 2: # Check status
			if haxState == 0: # MSET9 ID1 not present
				prbad("Can't do that now!")
				continue
			sanityReport()
			exitOnEnter()

		elif optSelect == 3: # Inject trigger file
			if haxState != 2: # Ready to inject
				prbad("Can't do that now!")
				continue
			injection(create=True)
			# exitOnEnter() # has it's own

		elif optSelect == 4: # Remove trigger file
			if haxState < 2:
				prbad("Can't do that now!")
			injection(create=False)
			time.sleep(3)
			return mainMenu()

		elif optSelect == 5: # Remove MSET9
			if haxState <= 0:
				prinfo("Nothing to do.")
				continue
			if haxState == 3:
				prbad("Can't do that now!")
				continue

			remove()
			remove_extra() # (?)
			exitOnEnter(remount=True)

mainMenu()
cleanup(remount=True)
prgood("Goodbye!")
time.sleep(2)
