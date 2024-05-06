

class GitModel():
	def __init__(self):
		self.url = None
		self.active_branch = None
		self.locked = None

		self.withlfs = False

		self.user_name = None
		self.user_email = None

	def load_from_dict(self, data):
		self.url = data["url"]
		self.active_branch = data.get("active-branch", "master")

		self.locked = data.get("locked", None)

		self.withlfs = data.get("lfs", False)

		self.user_name = data.get("user", self.user_name)
		self.user_email = data.get("email", self.user_email)

	def load_defaults(self, bucket):
		self.user_name = bucket.get_property("git-user")
		self.user_email = bucket.get_property("git-email")