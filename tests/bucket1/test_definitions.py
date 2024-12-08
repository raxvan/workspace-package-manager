

def load(database):
	database.set("TEST_TOKEN", "github.com")
	database.set("GITHUB_TOKEN", "")
	database.set("git-user", "raxvan")
	database.set("git-email", "razvan.om@gmail.com")

	database.add_git("pack-pyr", "https://{TEST_TOKEN}/raxvan/workspace-package-manager.git").branch("main")
	database.add_git("pack-pywr", "https://{GITHUB_TOKEN}github.com/raxvan/workspace-package-manager.git").branch("main")
	

