
from sortedcontainers import SortedSet
import ttkbootstrap as ttk

from artrefsync.ui.tag_post_manager import TagPostManager

class Post_Tree(ttk.Treeview):
    def __init__(self, root, **kwargs):
        self.tag_post_manager:TagPostManager = None
        self.image_set = SortedSet()
        self.detached_set = SortedSet()
        self.columns = ("Name")
        ttk.Style().configure("Treeview", background = "#222222")
        super().__init__(root, columns=self.columns, show= "tree", *kwargs)
        self.column("#0", width = 150, anchor='w', stretch=False)

        # threadCaller.add(self.init_tag_post_manager, self.init_image_frame)
    
    def populate_tree(self, tag_post_manager):
        self.tag_post_manager = tag_post_manager
        self.image_set.update(self.tag_post_manager.post_set)
        for i in reversed(range(len(self.image_set))):
            val = self.image_set[i]
            # self.insert("", "end", iid=val, values=(val,))
            self.insert("", "end", iid=val, text=val)
    
    def refresh(self, filter_set):
        if self.tag_post_manager:
            filtered_posts = SortedSet(self.tag_post_manager.get_posts(filter_set))
            print(f"Number of filterd Posts: {len(filtered_posts)}")
            for p in filtered_posts[-10:-1]:
                print(p)

            

            to_attach = self.detached_set.union(filtered_posts) 
            to_detach = self.image_set.difference(filtered_posts)
            self.detached_set.difference_update(to_attach)
            self.image_set.difference_update(to_detach)
            self.detached_set.update(to_detach)
            self.image_set.update(to_attach)
            for d in to_detach:
                self.detach(d)
                

            # starting_len = len(self.get_children(''))
            for pid in reversed(to_attach):

                # index = self.image_set.index(pid)
                # rev_index = starting_len + i - 1
                self.move(pid, "", "end")


                





            

            
            

            



        


